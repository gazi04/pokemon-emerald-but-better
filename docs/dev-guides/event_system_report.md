# Event System — How It's Written, How It Works, How It Connects

## 1. What it is, in one line

The event system is a **tiny synchronous publish/subscribe bus**: any layer fires a typed event object, and any other layer that subscribed to *that type* gets called back — neither side holds a reference to the other. It is the project's one cross-layer communication channel .

---

## 2. The two files

The whole system is two small files in `src/core/`:

| File | Role | LOC |
|---|---|---|
| `event_bus.py` | The bus itself — `subscribe` / `unsubscribe` / `publish`, plus the `global_bus` singleton | ~29 |
| `events.py` | Every event type, as a `@dataclass`, grouped by phase | ~126 |

That is the entire mechanism. No threads, no queue, no async — `publish` calls each listener inline.

---

## 3. How it's written — the bus

```python
class EventBus:
    def __init__(self):
        self._subscribers: Dict[Type, List[Callable]] = {}

    def subscribe(self, event_type: Type, listener: Callable[[Any], None]):
        self._subscribers.setdefault(event_type, [])
        if listener not in self._subscribers[event_type]:   # dedupe
            self._subscribers[event_type].append(listener)

    def unsubscribe(self, event_type: Type, listener):
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(listener)
            except ValueError:
                pass   # not subscribed — ignore

    def publish(self, event: Any):
        for listener in self._subscribers.get(type(event), []):
            listener(event)

global_bus = EventBus()
```

Three properties worth knowing:

- **Keyed by type, not by string.** The dict key is the event *class* (`SwapViewEvent`), not a name string. `publish` looks up `type(event)`. A typo'd event name is a normal Python `NameError`, not   a silent dead-end — the type checker guards it.
- **Subscribe is idempotent.** The `if listener not in` guard means double-subscribing the same callback is a no-op. This matters because views subscribe in `on_show_view`, which can fire more than once.
- **Unsubscribe is forgiving.** Removing a listener that was never added is silently ignored — safe to call in teardown without tracking whether you ever subscribed.

**The `global_bus` singleton** is what everyone imports. There is one bus for the whole process; no one constructs their own.

---

## 4. How it's written — the events

`events.py` is *only* dataclasses — no logic. They are grouped by game phase:

| Group | Events | Fired by |
|---|---|---|
| **Overworld** | `PlayerFinishedMoveEvent`, `BattleEncounterTriggeredEvent` | `MovementSystem`, `EncounterSystem` |
| **NPC** | `NpcInteractEvent` | `player_input` controller |
| **Battle** | `TextMessageEvent`, `HpChangedEvent`, `PokemonFaintedEvent` | `BattleSystem` |
| **Navigation** | `SwapViewEvent`, `CloseViewEvent`, `OverlayViewEvent` | every view (via `GameView` base verbs) |
| **Save/Load** | `SaveGameRequestEvent`, `SaveCompletedEvent` | `MenuView`, `GameDirector` |

An event is a plain data carrier:

```python
@dataclass
class BattleEncounterTriggeredEvent:
    """Fired by EncounterSystem when a wild battle should start."""
    pokemon_name: str
    pokemon_data: PokemonSpecies
    pokemon_level: int
```

The dataclass *is* the contract between publisher and subscriber. The fields are the payload; the docstring says who fires it and when.

---

## 5. How it connects — the data flow

The bus decouples the three architectural layers. A system never imports a view; a view never imports another view. They only share the event type.

```
 PUBLISHER                         BUS                       SUBSCRIBER
 (systems / views / controllers)                            (views / director / systems)

 EncounterSystem ── publish(BattleEncounterTriggeredEvent) ─▶ global_bus ─▶ OverworldView._on_battle_triggered
 MovementSystem  ── publish(PlayerFinishedMoveEvent) ───────▶ global_bus ─▶ EncounterSystem._on_player_moved
 player_input    ── publish(NpcInteractEvent) ─────────────▶ global_bus ─▶ OverworldView._on_npc_interaction
 BattleView      ── publish(OverlayViewEvent) ─────────────▶ global_bus ─▶ GameDirector._on_overlay_view
 MenuView        ── publish(SaveGameRequestEvent) ─────────▶ global_bus ─▶ GameDirector._on_save_request
 GameDirector    ── publish(SaveCompletedEvent) ───────────▶ global_bus ─▶ MenuView._on_save_completed
```

Two connection hubs dominate:

**The `GameDirector` is the navigation hub.** In its `__init__` it subscribes to all three nav events plus save:

```python
global_bus.subscribe(SwapViewEvent,    self._on_swap_view)
global_bus.subscribe(CloseViewEvent,   self._on_close_view)
global_bus.subscribe(OverlayViewEvent, self._on_overlay_view)
global_bus.subscribe(SaveGameRequestEvent, self._on_save_request)
```

Views never call `window.show_view()` themselves. They publish a nav event; the Director receives it and builds/shows the target view from the event's `payload` dict. This is *why* views don't import each other — the Director is the only thing that knows every view class.

**The overworld↔battle chain** shows a multi-hop flow with no direct coupling:

```
player walks → MovementSystem.publish(PlayerFinishedMoveEvent)
            → EncounterSystem (subscribed) rolls for an encounter
            → EncounterSystem.publish(BattleEncounterTriggeredEvent)
            → OverworldView (subscribed) catches it
            → OverworldView.swap("battle", ...) → publish(SwapViewEvent)
            → GameDirector (subscribed) builds BattleView
```

`MovementSystem` has no idea `EncounterSystem` exists; `EncounterSystem` has no idea the overworld view exists. Each only knows its event type.

---

## 6. The navigation verbs (the ergonomic layer)

Most views don't call `global_bus.publish(...)` directly. The `GameView` base class (`src/states/base_view.py`) wraps the three nav events in readable verbs:

```python
def overlay(self, target, **payload):
    global_bus.publish(OverlayViewEvent(target=target, payload=payload))

def swap(self, target, **payload):
    global_bus.publish(SwapViewEvent(target=target, payload=payload))

def close(self):
    global_bus.publish(CloseViewEvent())
```

So a view writes `self.overlay("bag", previous_view=self, battle_system=self.battle_system)` instead of spelling out the event. This is the discoverable, autocomplete-friendly front door; the raw bus is still there underneath.

---

## 7. How to use it

### Define an event
Add a `@dataclass` to `events.py`, in the right phase group, with a docstring saying who fires it:

```python
@dataclass
class ItemPickedUpEvent:
    """Fired by the overworld when the player walks onto a ground item."""
    item_id: str
    quantity: int
```

### Publish it
From the producing system/view, import `global_bus` and the event, then fire it:

```python
from src.core.event_bus import global_bus
from src.core.events import ItemPickedUpEvent

global_bus.publish(ItemPickedUpEvent(item_id="potion", quantity=1))
```

The publisher does not know or care if anyone is listening — zero subscribers is fine.

### Subscribe to it
In the consumer, register a callback that takes the event as its one argument:

```python
def on_show_view(self):
    global_bus.subscribe(ItemPickedUpEvent, self._on_item_picked_up)

def on_hide_view(self):
    global_bus.unsubscribe(ItemPickedUpEvent, self._on_item_picked_up)

def _on_item_picked_up(self, event: ItemPickedUpEvent):
    self.show_toast(f"Got {event.quantity}× {event.item_id}")
```

### For a new view target — use the verbs, not the bus
Don't add a new nav event. Publish `OverlayViewEvent`/`SwapViewEvent` via the base verbs, add a `_build_<target>` method, and register it in `GameDirector._overlay_builders` / `_transient_builders` (the dispatch registries that replaced the old `if target == "...":` ladders):

```python
# in the view:
self.overlay("shop", previous_view=self, items=stock)

# in GameDirector: one builder method...
def _build_shop(self, payload):
    from src.states.shop_view import ShopView
    return ShopView(self.player_manager, self.data_loader, **payload)

# ...and one registry entry in __init__:
self._overlay_builders = { ..., "shop": self._build_shop }
```

---

## 8. Lifecycle rules (the gotchas)

- **Subscribe in `on_show_view`, unsubscribe in `on_hide_view`.** A view that subscribes but never unsubscribes keeps receiving events while off-screen — and, because the bus holds the bound method, it can't be garbage-collected. `OverworldView` and `MenuView` follow this pair.
- **Subscribe is safe to repeat; unsubscribe is safe to over-call.** The dedupe + forgiving-remove design means you don't have to track subscription state defensively.
- **`publish` is synchronous and ordered.** Listeners run inline, in subscription order, on the caller's stack. A slow or throwing listener blocks/breaks the publisher. Keep handlers light.
- **A handler that publishes re-enters the bus.** This is how the encounter chain works (one publish triggers a handler that publishes again) — intended, but watch for accidental loops.

---

## 9. Where it sits in the architecture

```
 model      (pure data — no bus)
   ▲
 systems    ── publish ──▶  global_bus  ◀── subscribe ── states (views)
   ▲                           ▲                              │
   └──────── subscribe ────────┘                              │ publish (nav)
                                                              ▼
                                                        GameDirector
```

The bus is the seam that lets `systems/` stay arcade-free and lets views stay ignorant of each other. It is the backbone the rest of the layering (model → systems → states/ui) is built on.

---

## 10. Honest limitations

- **No event history / replay.** Fire-and-forget; a subscriber that wasn't listening at publish time misses the event forever.
- **`payload: dict` on nav events is stringly-typed.** `SwapViewEvent.payload["pokemon_name"]` is not type-checked — a key typo fails at the receiving builder, not at publish.
- **Single global bus.** Fine for a solo game; there is no scoping/namespacing if the project ever needed isolated event channels.
- **Synchronous coupling on cost.** Because listeners run inline, an expensive handler silently taxes the publisher. No timing or isolation between subscribers.
