# The View Layer (`src/states/`) — How It's Written, How It Works, How It Connects

## 1. What the view layer is, in one line

`src/states/` holds the **screens** — every `arcade.View` subclass the player looks at. A view owns input handling, a UI object to draw, and the wiring between them; it **never constructs another view or calls `window.show_view()` for navigation** — it publishes a navigation event and lets the `GameDirector` build the target. Views are the only layer that touches `arcade` *and* game systems.

> Contract: views publish `SwapViewEvent` / `OverlayViewEvent` / `CloseViewEvent`; the Director subscribes and shows the right view. See `game_director_report.md` and `event_system_report.md`.

---

## 2. The cast — 13 files, three roles

| File | Class | Role | Kind | LOC |
|---|---|---|---|---|
| `base_view.py` | `GameView` | Shared base: input + nav verbs + lifecycle defaults | base | 39 |
| `overworld_view.py` | `OverworldView` | The map screen — movement, NPCs, encounters | **persistent** | 246 |
| `battle_view.py` | `BattleView` | Wild/trainer battle screen | transient (swap) | 457 |
| `evolving_view.py` | `EvolvingView` | Post-battle evolution animation | transient (swap) | 178 |
| `dialog_view.py` | `DialogView` | NPC conversation box | overlay | 71 |
| `menu_view.py` | `MenuView` | Start menu (Pokédex/Party/Bag/Save) | overlay | 85 |
| `bag_view.py` | `BagView` | Inventory + pokeball use | overlay | 143 |
| `pokemon_menu_view.py` | `PokemonMenuView` | Party list (switch/move/use/info) | overlay | 155 |
| `pokemon_info_view.py` | `PokemonInfoView` | Single-Pokémon stat tabs | overlay | 40 |
| `pokedex_view.py` | `PokedexView` | Seen/owned species list | overlay | 45 |
| `shop_view.py` | `ShopView` | Poké Mart buy screen | overlay | 138 |
| `map_loader.py` | `MapLoader` / `LoadedMap` | Builds a map's runtime objects (no view) | helper | 111 |
| `battle_transition.py` | `BattleTransition` | Pre-battle flicker timer | helper | 33 |

Eleven are actual views (10 screens + the base). Two — `MapLoader` and `BattleTransition` — are **extracted collaborators** that live here because they serve `OverworldView`, but hold no view code themselves (the SRP split from `readability_refactor_plan.md`).

---

## 3. The base class — `GameView`

Every screen subclasses `GameView` (`base_view.py`). It removes the wiring each view used to repeat:

- **`is_pressed(config_key, symbol)`** — the one input-mapping helper, formerly copy-pasted in nine files. `config_key` is a resolved `CONFIG.controls` value.
- **`on_draw` / `on_update` defaults** — clear + `self.ui.draw()`, and `self.ui.update(dt)` if the UI has one. Read via `getattr` so the base **never constrains a subclass's `ui` type** (a typed `ui` attribute regressed pyright ~250 errors — documented gotcha).
- **Navigation verbs** — `self.overlay(target, **payload)`, `self.swap(target, **payload)`, `self.close()`. These are the discoverable front door over `global_bus.publish(...Event(...))`.

So a typical view writes `self.overlay("bag", previous_view=self)` instead of building the event by hand. Views needing custom rendering (overworld, battle, evolving) override `on_draw`/`on_update` and ignore the defaults.

---

## 4. The three view kinds (the navigation contract)

The whole layer divides by *how the Director shows it* (`game_director_report.md`):

### Persistent — `OverworldView`
Built **once**, cached in `GameDirector._view_cache`, never re-instantiated. It holds `PlayerMotion`, `MovementSystem`, `EncounterSystem`, `NpcController`, the camera. Returning from any battle/menu just re-shows this same instance, so the world state survives.

### Transient (swap) — `BattleView`, `EvolvingView`
Full-screen takeovers, built **fresh** each time from the event payload, discarded on exit. Reached via `self.swap("battle", ...)`; they leave via `self.close()`, which returns to the cached overworld.

### Overlay — `MenuView`, `BagView`, `PokemonMenuView`, `PokemonInfoView`, `PokedexView`, `ShopView`, `DialogView`
Stacked **on top** of whatever is showing, without destroying it. They keep a `previous_view` reference and pop back with `self.window.show_view(self.previous_view)`. The ones drawn over the live world (`menu`, `dialog`, `shop`) call `self.overlay.on_draw()` first to paint the background.

---

## 5. How a view is written — the common shape

Every view follows the same skeleton:

```python
class SomeView(GameView):
    def __init__(self, previous_view, ...injected deps...):
        super().__init__()
        self.ui = SomeUi()              # owns a UI object from src/ui/
        self.system = SomeSystem(...)   # optional: a logic system from src/systems/
        # ...local cursor/index state...

    def on_key_press(self, symbol, modifiers):
        if self.is_pressed(CONFIG.controls.up, symbol): ...
        elif self.is_pressed(CONFIG.controls.interact, symbol): self._act()

    def on_draw(self):                  # often inherited from GameView
        self.clear(); self.ui.draw()
```

Three rules hold across the layer:

1. **Dependencies are injected**, never imported globally — the Director passes `player_manager`, `data_loader`, `message_service` into each constructor.
2. **The view owns presentation + input; logic lives in a system.** `BagView` drives a `BagSystem`, `PokemonMenuView` drives a `PokemonMenuSystem`, `BattleView` drives a `BattleSystem`. The view reads cursor state and calls system methods; it doesn't compute game rules itself.
3. **Navigation is a verb, not a call** — `self.overlay/swap/close`, except overlay *return* which is a direct `show_view(previous_view)` (a stack pop, not a nav decision).

---

## 6. `OverworldView` — the hub (and the god object)

The biggest real view. It does eight jobs (the SRP audit flags it):

- **Construct from save** — reads `save_manager.saved_position`, sets map/direction/pixel, calls `setup()`.
- **`setup()`** delegates map building to `MapLoader` (tilemap, scene, NPCs, controller, bush set) and rebuilds the `EncounterSystem`.
- **Subscriptions** — on show, subscribes to `BattleEncounterTriggeredEvent` + `NpcInteractEvent` (and resubscribes the encounter system); on hide, tears them all down. Also clears the message box so a stray bark can't queue into a dead box.
- **Game loop** (`on_update`) — runs the `BattleTransition` flicker if active, lerps the camera, polls input → movement, handles map transitions, and ticks `NpcController` (NPCs only think while the overworld is active, so they freeze during menus/battle).
- **Event reactions** — `_on_battle_triggered` starts the flicker; `_on_npc_interaction` resolves dialog state via `_resolve_dialog` and overlays the dialog. As of 2026-06-25 the old `if npc_id == "poke-mart-npc": overlay("shop")` hardcode is **gone** — every NPC (clerk included) routes through the dialog, and `DialogView` opens the shop/heal/fight via the NPC's `action_after_dialog` data. Adding a role-NPC needs no overworld edit.
- **`respawn_at_pokecenter()`** — the whiteout relocation, called by `BattleView`.

`_resolve_dialog` is a small state machine over NPC battle progress: unbeaten battle-NPC → `first_encounter`/`fight`; beaten → `after_victory`/`end`; else → `default`. What happens *after* the dialog is dispatched in `DialogView._action_handlers` (`{"shop"|"fight"|"heal": handler}`, default close) — a `make_behavior`-style table keyed on `action_after_dialog`.

> The two helpers it leans on — `MapLoader` (pure map build) and `BattleTransition` (flicker timer/state) — were extracted *out* of this view to shrink it. More extraction (input, nav) is tracked but YAGNI-deferred.

---

## 7. `BattleView` — the largest screen

457 LOC, three responsibilities (covered in depth elsewhere): **input routing** (`on_key_press`), **FSM dispatch** (`what_happend_after_text` reacting to `BattleSystem.battle_state`), and **sprite/UI sync** (`_refresh_active_pokemon_ui`, `set_enemy`). It constructs its own `BattleSystem`, holds `BattlePokemon` + `PokemonSprite` pairs for both sides, and routes battle text through the injected `MessageService`. Wild enemies now get their moves from `wild_moveset.select_wild_moves` (species learnset, by level) instead of a hardcoded Tackle. The pure decisions (exp award, catch, caught-add) already moved into `BattleSystem`; the full `BattleFlowController` split is YAGNI-deferred (`readability_refactor_plan.md`§6).

---

## 8. How they connect — navigation flows

Two real flows show the contract end-to-end.

**Wild encounter (swap):**
```
 OverworldView._on_battle_triggered  (BattleEncounterTriggeredEvent)
   → BattleTransition.start(...)        # flicker
   → on_update sees flicker done → self.swap("battle", pokemon_name=…, pokemon_data=…)
        → GameDirector._on_swap_view → builds BattleView → show_view
 ... battle ends → BattleView.close() → Director shows cached OverworldView
```

**Bag from the menu (overlay chain):**
```
 OverworldView: press bag → self.overlay("menu")
   → MenuView (select Bag) → self.overlay("bag", previous_view=self)
        → BagView (select item) → self.overlay("pokemon_menu", previous_view=self, bag=…, item_index=…)
             → PokemonMenuView → use item via BagSystem → show_view(previous_view)   # pops back
```

Note the two return styles: a transient battle **closes** (nav decision → Director), while an overlay **pops** by `show_view(self.previous_view)` (it knows exactly where it came from). The cross-view calls in the overlay chain (`previous_view.update_item()`, `previous_view.switch_turn()`, `previous_view.start_catch_attempt(result)`) are how a child overlay hands a result back up — a direct method call on the held `previous_view`, *not* the bus.

---

## 9. Subscriptions & the message box (lifecycle gotchas)

- **Views that listen subscribe in `on_show_view`, unsubscribe in `on_hide_view`.** `OverworldView` (encounter + NPC events) and `MenuView` (`SaveCompletedEvent`) both follow the pair; skipping it leaves a view reacting while off-screen and uncollectable (the bus holds the bound method).
- **The active text box is registered on show.** `BattleView`/`DialogView` call `self.message_service.set_box(self.ui.message_box)` in `on_show_view`; `OverworldView` clears it with `set_box(None)`. This is why text routes to the right box without callers knowing which view is up (`message_service_report.md`).
- **Some overlays toggle their UIManager** — `PokedexView` enables/disables `ui._manager` on show/hide so arcade GUI widgets don't leak across screens.

---

## 10. The two helpers (extracted from `OverworldView`)

**`MapLoader` → `LoadedMap`.** Pure map build from a `.tmx` path: loads the tilemap + scene, spawns NPCs from the `npc` object layer (each with a `make_behavior(props)` behavior), builds the `NpcController`, and extracts the bush-tile set (once, for O(1) encounter lookups). Returns a `LoadedMap` dataclass the overworld wires in. No view/render state — that's the point of the split.

**`BattleTransition`.** Owns the pre-battle screen-flicker timer. `start(name, level, data)` arms it; `update(dt)` toggles `can_render_scene` for the flicker and returns the pending battle tuple on the frame it completes (else `None`), which the overworld turns into a `swap("battle", ...)`. Keeps the flicker timer out of `OverworldView.on_update`.

---

## 11. How to use it

### Add a new screen
1. Subclass `GameView`; take `previous_view` + injected deps in `__init__`; set `self.ui`.
2. Handle input in `on_key_press` via `self.is_pressed(CONFIG.controls.X, symbol)`.
3. Register the builder in `GameDirector` (`_build_overlay_view` or `_build_transient_view`) keyed by a target string — the Director is the only place that imports the view class.

### Navigate from a view
```python
self.overlay(
    "bag", previous_view=self, battle_system=self.battle_system
)  # stack on top
self.swap(
    "battle", pokemon_name=name, pokemon_data=data, pokemon_level=lvl
)  # full takeover
self.close()  # back to overworld
```

### Return from an overlay
```python
self.window.show_view(
    self.previous_view
)  # pop the stack (you know where you came from)
# hand a result up if needed:
if hasattr(self.previous_view, "start_catch_attempt"):
    self.previous_view.start_catch_attempt(result)
```

### Drive game logic
Never compute rules in the view — call a system: `self.bag_system.use_item(...)`, `self.battle_system.turn(...)`, `self.system.confirm_switch(...)`. Mutate save state through `PlayerManager`.

---

## 12. Conventions & known debt

- **Director owns construction; views own presentation.** A view that `import`s another view class is a smell — go through a nav verb + Director builder instead.
- **Persistent vs transient vs overlay is a real distinction** — don't cache a transient, don't `close()` an overlay (it'd jump to the overworld instead of popping back).
- **Known debt:** `BattleView` (457) and `OverworldView` (246) are the two big views (SRP audit). `pokemon_menu_view.py` was converted to snake_case (`_handle_menu_input`, `_handle_tooltip_input`, `team_index`) on 2026-06-25 — the plan §4 holdout is closed. `bag_view`/`pokemon_menu_view` still reach through `previous_view.previousWindow` chains for battle-item use — fragile coupling, works but flagged (that camelCase pair is intentionally left, spanning `game_director`/`bag_view`).
