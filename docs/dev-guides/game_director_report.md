# GameDirector — Report & Guide

## 1. What it is

`GameDirector` is the one object that decides *which `arcade.View` is on screen*. It sits directly beneath the `arcade.Window` (created in `main.py`) and nothing else is allowed to call `window.show_view(...)`. Views never navigate themselves — they **publish an event**, the Director hears it and swaps the screen. That single rule is what keeps navigation legible: to learn every way the game can change screens, you read one file.

It owns three things:
- the long-lived **service singletons** (`SaveManager`, `DataLoader`, `PlayerManager`, `MessageService`),
- a **view cache** (`_view_cache`) that keeps the Overworld alive for the whole session,
- the **navigation subscriptions** on the global event bus.

---

## 2. How it's written

### Construction (`__init__`, lines 32-45)
```python
def __init__(self, window: arcade.Window):
    self._window = window
    self._view_cache: dict[str, arcade.View] = {}

    self.save_manager = SaveManager()
    self.data_loader = DataLoader()
    self.player_manager = PlayerManager(self.save_manager, self.data_loader)
    self.message_service = MessageService()

    global_bus.subscribe(TextMessageEvent, self.message_service.on_message_event)
    global_bus.subscribe(SwapViewEvent, self._on_swap_view)
    global_bus.subscribe(CloseViewEvent, self._on_close_view)
    global_bus.subscribe(OverlayViewEvent, self._on_overlay_view)
    global_bus.subscribe(SaveGameRequestEvent, self._on_save_request)
```

The Director **builds the services once** and hands the *same instances* to every view it constructs. That is the cure for the old "two `SaveManager`s" divergence bug — there is exactly one of each, and they live here.

### Two structural patterns worth noting
- **Lazy view imports.** Every `from src.states.X import XView` sits *inside* the method that builds it, not at module top. Views import from `core`, and `core` would import views → a circular import.  Importing at call-time breaks the cycle.
- **Dispatch registries (`{target: builder}`).** Two dicts built in `__init__` — `_transient_builders` and `_overlay_builders` — map a string key to a per-screen `_build_<target>(payload)` method. `_build_transient_view`/`_build_overlay_view` are now a one-line lookup (`self._transient_builders.get(target)`) instead of an `if target == "...":` ladder. Each builder holds the lazy import + constructor; services (`player_manager`, `data_loader`, `message_service`) are injected from the Director's own fields, only *screen-specific* data comes from the event `payload`. This mirrors `npc_behaviors.make_behavior` — adding a screen no longer edits a shared branch.

---

## 3. How it works — the three navigation verbs

Views publish one of three events (via the `GameView` base helpers `self.swap/overlay/close`, see `src/states/base_view.py`). The Director's handlers turn each into a `window.show_view(...)`.

| Event | Handler | Meaning | Example targets |
|---|---|---|---|
| `SwapViewEvent(target, payload)` | `_on_swap_view` | **Full takeover** — replace the screen with a *fresh* transient view | `battle`, `battle_trainer`, `evolving`, `overworld` |
| `OverlayViewEvent(target, payload)` | `_on_overlay_view` | **Stack on top** — open a menu without destroying what's underneath | `menu`, `bag`, `pokemon_menu`, `dialog`, `shop`, `pokedex`, `pokemon_information` |
| `CloseViewEvent()` | `_on_close_view` | **"I'm done"** — return to the cached Overworld | — |

### Swap (transient, fresh each time)
`_on_swap_view` special-cases `"overworld"` (show the cached singleton), otherwise calls `_build_transient_view`, which constructs a **brand-new** `BattleView`/`EvolvingView` from the payload. Transient views are disposable — a new battle every encounter.

### Overlay (stack, services injected)
`_on_overlay_view` → `_build_overlay_view` constructs the menu/bag/etc. Overlays read `payload.get("previous_view", overworld)` so they know who to return to, and pull services from the Director. Because the Overworld is never destroyed, opening the Bag mid-battle or the menu in the field leaves the underlying state intact.

### Close (back to Overworld)
`_on_close_view` just shows the cached Overworld. Any transient view (battle won/lost, evolution finished) publishes `CloseViewEvent()` to get home.

### The Overworld singleton (`_get_or_create_overworld`, lines 95-103)
Built once, cached in `_view_cache["overworld"]`, reused forever. This is why the player's position, loaded map, and NPC state survive every menu, battle, and dialog — the view holding that state is never thrown away.

---

## 4. How it connects

```
                         main.py
                            │ creates arcade.Window
                            ▼
                      GameDirector ──owns──► SaveManager, DataLoader,
                            │                 PlayerManager, MessageService
              subscribes   │   publishes
        ┌───────────────── global_bus (EventBus singleton) ─────────────────┐
        │                                                                    │
   Views publish:                                            Director shows the view:
   self.swap/overlay/close(...)  ──►  Swap/Overlay/CloseViewEvent  ──►  window.show_view(...)
```

- **Upstream:** `main.py` instantiates the window, hands it to `GameDirector(window)`, calls `director.start()`, then `arcade.run()`.
- **Sideways (the bus):** `src/core/event_bus.py::global_bus` is the only channel. The Director  subscribes in `__init__`; views publish through the `GameView` nav verbs. Publisher and Director never reference each other directly — the bus decouples them.
- **Downstream (the views):** the builder ladders construct the ten `arcade.View` subclasses in `src/states/`. Each gets the shared services + its slice of `payload`.
- **Save path:** `SaveGameRequestEvent` (published by `MenuView`) → `_on_save_request` captures NPC state, calls `save_manager.flush_save(overworld.player_state)`, and replies with `SaveCompletedEvent(success=...)` so the menu can show feedback.
- **Text routing:** the Director also wires `TextMessageEvent → message_service.on_message_event`, so any system can push dialogue to the active text box without a view reference (see `message_service_report.md`).

### Payload contract
The `payload: dict` is the **only** thing a publisher must get right. Keys are read with `payload.get(...)` and sane defaults, except the battle target which requires `pokemon_name`/`pokemon_data`/`pokemon_level`. Services are **never** passed in the payload — they come from the Director.

---

## 5. How to use it

### Boot the game (already done in `main.py`)
```python
window = arcade.Window(...)
director = GameDirector(window)
director.start()      # builds + shows the Overworld
arcade.run()
```

### Navigate from inside a view
Subclass `GameView` (`src/states/base_view.py`) and use the verbs — do **not** call `window.show_view` yourself:
```python
# full takeover into a wild battle
self.swap("battle", pokemon_name=name, pokemon_data=data, pokemon_level=level)

# stack the Bag on top, remembering who to return to
self.overlay("bag", previous_view=self, battle_system=self.battle_system)

# done — go back to the Overworld
self.close()
```

### Add a brand-new screen (the common extension)
1. Write the `XView(GameView)` in `src/states/`.
2. Add a `_build_<target>(self, payload)` method (lazy import + constructor inside it):
   ```python
   def _build_my_screen(self, payload: dict):
       from src.states.my_view import MyView
       return MyView(previous_view=payload.get("previous_view", self._get_or_create_overworld()),
                     player_manager=self.player_manager,
                     data_loader=self.data_loader)
   ```
3. Register it in the right dict in `__init__`:
   - full-screen/disposable → `_transient_builders`
   - stacked menu → `_overlay_builders`
   ```python
   self._overlay_builders = { ..., "my_screen": self._build_my_screen }
   ```
4. Publish `self.overlay("my_screen", ...)` (or `self.swap`) from wherever it's triggered.

The loop: **one builder method + one dict entry + one publish call** — the dispatch methods themselves never change.

---

## 6. Gotchas & current rough edges

- **Keep imports lazy.** Adding a `from src.states...` at module top will reintroduce the circular import. Always import inside the builder branch.
- **String keys are unchecked.** A typo'd `target` misses the registry (`.get(target)` → `None`), so `show_view` is silently skipped → nothing happens. There is no compile-time guard.
- **The Open/Closed smell is fixed.** The old `if target == "...":` ladders are now `{target: builder}` registries (`_transient_builders`/`_overlay_builders`), so adding a screen registers a new entry instead of editing a shared branch. (Done 2026-06-25, mirrors `npc_behaviors.make_behavior`.)
- **Save only works from the Overworld.** `_on_save_request` checks the cached view *is* an  `OverworldView`; saving from elsewhere returns `success=False`.

---

## 7. One-paragraph summary

`GameDirector` is the project's navigation hub: it owns the four service singletons and the Overworld cache, subscribes to three navigation events plus a save event on `global_bus`, and is the only code allowed to call `window.show_view`. Views stay ignorant of each other — they publish `swap`, `overlay`, or `close`, and the Director builds and shows the right `arcade.View`, injecting shared services and the event payload. To extend it you add one builder branch and one publish call.
