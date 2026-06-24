# Message Service — How It's Written, How It Works, How It Connects

## 1. What it is, in one line

`MessageService` is the **single endpoint for showing UI text**. Any view or system asks it to display a line or a list of lines; it routes that to whichever on-screen text box is currently active. It owns no rendering and no game logic — it is a thin router wired through dependency injection.

---

## 2. The three layers

The feature is deliberately split across three layers so that *routing*, *rendering*, and *event delivery* never bleed into one another.

```
 callers (views / systems)          "I want to show text"
        │
        ▼
 MessageService          (src/core/message_service.py)   ── WHERE text goes (routing)
        │   self._box
        ▼
 TypewriterMessageBox    (src/ui/components/...)          ── HOW text appears (rendering)
        │
        ▼
 arcade.gui.UILabel                                       ── the actual pixels
```

| Layer | File | Responsibility | Knows about |
|---|---|---|---|
| **Router** | `src/core/message_service.py` | Pick the active box; queue text onto it | A `MessageBox` *Protocol* only — no `arcade`, no `ui` |
| **Engine** | `src/ui/components/typewriter_message_box.py` | Queue, typewriter animation, completion callbacks | `arcade.gui` |
| **Surface** | `arcade.gui.UILabel` | Draw glyphs | — |

Key design rule: the router lives in `core` and must stay free of any `ui`/`arcade` import. It achieves that by depending on a **structural `Protocol`**, not the concrete box class.

---

## 3. How `MessageService` is written

Full current source (`src/core/message_service.py`):

```python
class MessageBox(Protocol):
    is_processing: bool
    def queue_message(self, message: str) -> None: ...
    def set_on_complete(self, callback: Callable) -> None: ...
    def clear(self) -> None: ...


class MessageService:
    def __init__(self) -> None:
        self._box: MessageBox | None = None

    def set_box(self, box: MessageBox | None) -> None:
        self._box = box

    def show(self, messages, callback=None) -> None:
        if self._box is None:
            _log.warning("show() with no active box; dropped: %s", messages)
            return
        if isinstance(messages, str):
            messages = [messages]
        for m in messages:
            self._box.queue_message(m)
        if callback:                       # one-shot — never clobbers the persistent callback
            self._box.set_on_complete(callback)

    def clear(self) -> None: ...
    def is_idle(self) -> bool: ...
    def on_message_event(self, event: TextMessageEvent) -> None:
        self.show(event.message)
```

Design choices worth calling out:

- **DI, not a singleton.** Exactly one instance, created and owned by `GameDirector`, injected into the views that need it. There is no module-level global (the old `game_context` global pattern was intentionally not reintroduced).
- **Duck-typed via Protocol.** `_box: MessageBox | None`. `TypewriterMessageBox` satisfies the protocol structurally; pyright verifies it at every `set_box(self.ui.message_box)` call site. This is what keeps `core` independent of `ui`.
- **Single active box, no stack.** The service points at *one* box at a time. The visible box-owning view registers it. 
- **`show()` normalizes input.** Accepts `str` or `list[str]`; a bare string becomes a one-element list, so callers never have to think about it.
- **No active box → logged warning, not a crash.** If nothing has registered a box, `show()`   logs a warning and returns. Safe, but visible in dev logs (no silent black hole).
- **One-shot callback.** A caller's `show(..., callback=fn)` registers a *one-shot* completion   on the box. It fires once when the queue drains, then clears itself — it can never overwrite or permanently re-fire the box's *persistent* callback (battle's turn flow).

---

## 4. How the engine (`TypewriterMessageBox`) works

The box is the part that actually animates and draws. Mechanics:

- **Queue.** `queue_message(text)` appends to `message_queue`; if idle, it immediately starts the next message.
- **Typewriter.** `update(dt)` (called from the owning view's `on_update`) reveals one  character at a time on a `TEXT_DELAY` timer. When a line is fully shown it waits ~1.5s, then  advances to the next queued line.
- **Two completion hooks (deliberately separate):**
  - `set_callback(fn)` — **persistent**. Fires after *every* queue-drain. Battle uses this for its turn flow (`what_happend_after_text`), set once at construction.
  - `set_on_complete(fn)` — **one-shot**. Fires once on the next drain, then is cleared. This is what `MessageService.show(callback=)` uses.
  - Drain order in `_next_message`: one-shot first (and cleared), then persistent.
- **`reset_prompt(text)`** — replaces the box contents with a static, non-animated prompt (used for "What will pokemon do?"); clears the queue, the processing flag, and any  pending one-shot. This replaced three lines of raw attribute-poking in `battle_view`.
- **`clear()`** — empties the queue, stops processing, drops the pending one-shot.

---

## 5. How callers connect to it

There are **two entry paths** into the service:

### Path A — direct call (views)
A box-owning view calls `self.message_service.show(...)` (or a wrapper that writes to the same box). Used when the caller already holds a reference to the service.

### Path B — over the event bus (systems)
Any system publishes `global_bus.publish(TextMessageEvent("..."))`. The service's `on_message_event` is subscribed to that event by `GameDirector`, so the system needs **no view reference and no service reference** — full decoupling.

```
view   ── message_service.show(str | list, callback?) ─┐
system ── global_bus.publish(TextMessageEvent("…"))   ─┤
                                                       ▼
                                  MessageService.on_message_event → show()
                                                       │
                                                       ▼
                                            active TypewriterMessageBox
```

---

## 6. Who owns a box, and when it's registered

The service points at one box; views set it. The rule:

> **Every *full* view sets the box it owns — or `None` — in `on_show_view`. Overlays never
> touch the box.**

| View | Owns a box? | What it does in `on_show_view` | Where |
|---|---|---|---|
| `battle_view` | yes (`self.ui.message_box`) | `set_box(self.ui.message_box)` | `battle_view.py:154` |
| `dialog_view` | yes (`self.ui.message_box`) | `set_box(self.ui.message_box)` | `dialog_view.py:41` |
| `overworld_view` | no | `set_box(None)` (drops any dead box) | `overworld_view.py` |
| `shop_view` | no (today) | `set_box(None)` when boxless | — |
| `bag` / `menu` / `pokemon_menu` (overlays) | no | nothing — they write to the box underneath | — |

Why boxless full views call `set_box(None)`: after a battle/dialog closes back to the overworld, the service would otherwise still point at the now-dead battle box. Clearing on the overworld's `on_show_view` means a stray system "bark" can't queue into a dead box.

Because every full view re-registers its box (or `None`) when re-shown, no **box stack** is needed — returning to a lower view restores its box automatically. (A stack was analysed and deferred; see the refactor doc's Known Limitations #2.)

---

## 7. End-to-end wiring (where each piece is created)

```
GameDirector.__init__                         (src/core/game_director.py)
  ├─ self.message_service = MessageService()
  ├─ global_bus.subscribe(TextMessageEvent, self.message_service.on_message_event)
  └─ injects self.message_service into:
        _get_or_create_overworld → OverworldView(..., message_service)
        _build_transient_view    → BattleView(..., message_service)   # "battle" + "battle_trainer"
        _build_overlay_view      → DialogView(..., message_service)
                                 → BagView(..., message_service)
```

`GameDirector` is the only place that knows about both the bus event and the views, which keeps `MessageService` itself bus-agnostic and trivially unit-testable.

---

## 8. Concrete call sites (current usage)

| Caller | Code | Notes |
|---|---|---|
| Battle turn / item / switch / catch | `self.ui.queue_messages(...)` (e.g. `battle_view.py:147,151,165`) | Goes through `BattleUiManager.queue_messages`, which writes straight to the same box the service points at (wrapper "option b"). |
| Battle prompt reset | `self.ui.message_box.reset_prompt(f"What will {name} do?")` (`battle_view.py:381`) | Replaced raw attribute-poking. |
| Battle turn-flow callback | `what_happend_after_text` set at `BattleUiManager` construction (`battle_ui_manager.py:27`) | The *persistent* callback. |
| Bag party-full | `previousWindow.show_messages([...])` (`bag_view.py`) | `BattleView.show_messages` (`battle_view.py:157`) does `switch_mode("dialog")` then `message_service.show(...)`, because the battle box is hidden in `"main"` mode. |
| Dialog lines | `self.ui.queue_messages(...)` (`dialog_view.py`) | `DialogUI.queue_messages` writes to the box directly. |
| Any system (future) | `global_bus.publish(TextMessageEvent("…"))` | No view reference required. |

Note on the **wrappers** (`BattleUiManager.queue_messages`, `DialogUI.queue_messages`): they were kept writing to the box directly rather than routed through the service ("option b"). The box is the *same object* the service points at, so behavior is identical; this avoided threading the service into the UI managers. The service is the single entry point for *new/system* callers and for the sites that previously poked the box raw.

---

## 9. Component connection map

```
                         ┌──────────────────────────────┐
                         │        GameDirector           │
                         │  owns MessageService          │
                         │  subscribes on_message_event  │
                         │  injects service into views   │
                         └───────┬───────────────┬───────┘
                    injects      │               │   subscribes
              ┌──────────────────┘               └──────────────┐
              ▼                                                  ▼
   ┌──────────────────────┐                          ┌────────────────────┐
   │  Views                │   set_box / show         │     global_bus     │
   │  battle / dialog      │─────────────────┐        │   TextMessageEvent │
   │  overworld(set None)  │                 │        └─────────┬──────────┘
   │  bag → show_messages  │                 │   on_message_event│
   └──────────┬────────────┘                 ▼                  │
              │ queue_messages    ┌────────────────────────┐    │
              │ (wrappers,        │     MessageService     │◄───┘
              │  same box)        │     self._box          │
              │                   └───────────┬────────────┘
              │                               │ queue_message / set_on_complete
              ▼                               ▼
   ┌────────────────────────────────────────────────────┐
   │            TypewriterMessageBox (engine)            │
   │   queue · typewriter · persistent + one-shot cb     │
   │            └─ arcade.gui.UILabel (pixels)           │
   └────────────────────────────────────────────────────┘
```

---

## 10. Strengths and current ceiling

**Strengths**
- One endpoint; callers don't know which view owns the box.
- `core` stays free of `ui` (Protocol boundary), so the service is unit-testable without arcade.
- Systems emit text with zero view coupling (bus path).
- Crash-visible: no-box `show()` logs instead of silently dropping.
- Persistent vs one-shot callbacks are separated, so `show(callback=)` is safe.

**Ceiling (documented, accepted)**
- One shared `message_queue` + single persistent callback: event "barks" can interleave with a view's scripted sequence, and `clear()` wipes everyone's pending text. Treat bus messages as fire-and-forget, never sequence-critical.
- The bus event carries only a string — it can't carry a callback. "Show this, then do X" needs a direct service reference.
- Every new text context (shop, signs, toasts) still needs its own box + a `set_box` call. The service answers "how to send," not "where it appears."
- No box stack yet — only needed if a box-owning view ever stacks over another *without* a view transition (e.g. a sub-textbox inside battle).

---

## 11. Usage guide

> Practical "how do I…" reference. (Ported from the standalone guide and corrected to the
> current code — notably: `show(callback=)` is now **one-shot**, and the bag party-full path is
> already wired.)

### 11.1 API at a glance

```python
service.show("A wild Rattata appeared!")             # single string
service.show(["Rattata used Tackle!", "It hit!"])    # multiple, queued in order
service.show("Go Torchic!", callback=self._on_done)  # run fn ONCE after the last msg (one-shot)
service.clear()       # wipe queue + stop
service.is_idle()     # True when nothing typing/queued
service.set_box(box)  # views call this in on_show_view — not for general callers
service.set_box(None) # clear active box (boxless full views call this on_show_view)
```

`TypewriterMessageBox` direct methods (when a view legitimately needs the box itself):

```python
box.reset_prompt("What will Torchic do?")  # replace display instantly, no typewriter, clears queue
box.clear()                                # wipe queue + stop processing
box.queue_message("text")                  # low-level enqueue (prefer service.show)
box.set_callback(fn)                       # PERSISTENT — fires after every queue-drain (battle turn flow)
box.set_on_complete(fn)                    # ONE-SHOT — fires once after the final message, then clears
box.show() / box.hide()                    # visibility — called by UI managers, not views
```

### 11.2 When to use what

| Situation | Use |
|---|---|
| View shows battle/dialog text | `self.message_service.show(...)` |
| System with no view reference | `global_bus.publish(TextMessageEvent("text"))` |
| "Show text, then do X once" | `service.show(..., callback=fn)` — one-shot; needs a direct service ref (can't go over the bus) |
| Persistent post-sequence hook (turn flow) | `box.set_callback(fn)` — set once, fires every drain |
| Replace a prompt instantly (no typewriter) | `self.ui.message_box.reset_prompt("What will X do?")` |
| Show battle text from another view (e.g. bag) | `previousWindow.show_messages([...])` — switches to dialog mode first |
| Static tooltip label (BagUI) | `bag_ui.set_text(...)` — not a queued message, leave alone |

### 11.3 Adding a new box-owning view

```python
# 1. Accept the service in the constructor
def __init__(self, message_service: MessageService, ...):
    self.message_service = message_service

# 2. Register the box when the view becomes active
def on_show_view(self):
    self.message_service.set_box(self.ui.message_box)

# 3. Show text anywhere in the view
self.message_service.show("You got Potion!")
```

Then wire it in `GameDirector._build_transient_view` or `_build_overlay_view`, passing`self.message_service`.

> **Overlays** (bag, menu, pokemon_menu): do **not** call `set_box`. They inherit whichever box
> the view underneath registered. Only *full* views call `set_box` — a box if they own one,
> `None` if they don't.

### 11.4 What NOT to do

```python
# BAD — raw attribute poke, breaks encapsulation, skips queue/processing reset
self.ui.message_box.target_text = "..."
self.ui.message_box.current_text = "..."
self.ui.message_box.dialog_text.text = "..."

# GOOD
self.ui.message_box.reset_prompt("...")  # static replacement, no typewriter
self.message_service.show("...")         # queued typewriter
```

### 11.5 Current wiring status

| File | Status |
|---|---|
| `battle_view` | Wired — `on_show_view` sets box (`battle_view.py:155`); `_reset_to_main_menu` uses `reset_prompt` (`battle_view.py:381`); exposes `show_messages()` (`battle_view.py:157`) |
| `dialog_view` | Wired — `on_show_view` sets box (`dialog_view.py:41`) |
| `overworld_view` | Wired — `on_show_view` calls `set_box(None)` (`overworld_view.py:105`), clearing the active box on return |
| `bag_view` | Wired — party-full calls `previousWindow.show_messages([...])` (`bag_view.py:121`). The **real-catch** path still uses `start_catch_attempt(result)` (`bag_view.py:132`) **by design** — that method does catch-specific work (mode switch + messages) beyond text |
| `menu_view`, `shop_view`, `pokedex_view`, `pokemon_menu_view`, `pokemon_info_view` | No text box; do not receive the service — fine |
| `evolving_view` | Renders its own text, not through the `MessageBox` protocol — fine |

> The earlier "Step 6 pending" note is **done**: party-full no longer rides the `start_catch_attempt({"messages": [...]})` dict. `start_catch_attempt` remains only for the real catch, which needs more than text.

### 11.6 Known limitations (status)

1. **Shared queue → interleave (callback clobber FIXED).** One `message_queue`, so bus "barks" can interleave with a scripted sequence and `clear()` wipes pending text — treat bus messages as fire-and-forget. *Callback ownership is now safe:* persistent (`set_callback`) and one-shot (`set_on_complete`) are separate, so `show(callback=)` can't clobber the turn-flow callback.
2. **No box stack — deferred (not a gap today).** Returning to a boxless view calls   `set_box(None)` and lower full views re-register on `on_show_view`, so no stale box survives. A stack is only needed for same-view nested sub-boxes.
3. **Silent drops → now logged.** `show()` with no active box logs a `WARNING` instead of   silently no-opping. (Queuing into a *wrong* box if a view forgot `set_box` is still   undetectable.)
4. **Bus path can't carry a callback.** `TextMessageEvent` is a single string. For "show then   do X," use a direct service reference.
5. **Every new text context needs its own box.** The service answers "how to send," not "where it appears." Shop, signs, item-pickup toasts each need a `TypewriterMessageBox` + `set_box`.
