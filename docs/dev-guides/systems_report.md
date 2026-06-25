# The Systems Layer — How It's Written, How It Works, How It Connects

## 1. What the systems layer is, in one line

`src/systems/` holds the **stateless game logic** — the rules of movement, encounters, battle, inventory, and NPCs. Systems mutate model state and publish events; they hold no `arcade` view code and never call `window.show_view()`. Views subscribe to their events and render the result.

> *"Systems — stateless logic, no arcade dependency. They publish events and mutate `SaveManager` state; views subscribe to those events to update UI."* One caveat lives below: `npc_controller.py` does import `arcade` (it does sprite-list collision), so it's the one "system" that's really overworld glue.

---

## 2. The ten files at a glance

| File | Class | One-job summary | Touches arcade? | Publishes events? |
|---|---|---|---|---|
| `movement_system.py` | `MovementSystem` | Tween an entity tile-to-tile | No | `PlayerFinishedMoveEvent` |
| `encounter_system.py` | `EncounterSystem` | Roll a wild battle on a grass step | No | `BattleEncounterTriggeredEvent` |
| `battle_system.py` | `BattleSystem` | Run a battle's turns | No | `HpChangedEvent`, `PokemonFaintedEvent` |
| `bag_system.py` | `BagSystem` | Use items / pokeballs from the bag | No | No (returns data) |
| `pokemon_menu_system.py` | `PokemonMenuSystem` | Reorder / switch the party | No | No |
| `wild_moveset.py` | `select_wild_moves` (fn) | Pick a wild foe's moves from its learnset by level | No | No |
| `npc_manager.py` | `NPCManager` | Track per-NPC interaction flags | No | No |
| `npc_behaviors.py` | `Behavior` + `make_behavior` | Decide what an NPC wants to do | No | No |
| `npc_controller.py` | `NpcController` | Drive every NPC each frame + walkability | **Yes** | No |
| `dialog_manager.py` | `DialogManager` | Pick the right dialog lines for an NPC's state | No | No |

Two natural clusters: the **overworld loop** (movement, encounter, the NPC trio, dialog) and the **battle/inventory stack** (battle, bag, pokemon-menu).

---

## 3. The shared pattern — how a system is written

Almost every system follows the same three-rule shape:

1. **Dependencies are injected** through `__init__` (a `PlayerManager`, a `DataLoader`, a    `player_state`), never imported as globals. This is why they're testable without a window.
2. **Methods return data or mutate the model** — they hand back `list[str]` messages or `bool`, and they write through Facades (`PlayerManager`), not raw save files.
3. **Cross-layer signalling is via `global_bus.publish(...)`**, never a direct call into a view.

The model to imitate (the scalability audit calls it out) is **`npc_behaviors.make_behavior`**: a factory over pluggable subclasses, configured from data. The `{key: handler}` dispatch-table form of it is now copied in four more places (all landed 2026-06-25): `BagSystem._effect_appliers`/`_effect_eligibility` (item effects), `BattlePokemon._effect_handlers` (move effects), `GameDirector._transient/_overlay_builders` (view construction), and `DialogView._action_handlers` (post-dialog NPC roles). New systems should follow that template.

---

## 4. The overworld loop

### `MovementSystem` — the tile tween
Pure motion math, no state of its own. It operates on *any* object exposing the `GridMotion`/`PlayerMotion` movement fields, so the **same instance drives both the player and NPCs**. Three methods:

- `begin(state, intent)` — if idle and given a `"move"` intent, lock in start/target pixels.
- `advance(dt, state)` — lerp pixel position toward target; on the completion frame snap to the tile, recompute `grid_x/grid_y`, and return `True`.
- `update(dt, state, intent)` — the player-only wrapper: `begin` + `advance`, and on completion **publishes `PlayerFinishedMoveEvent`** (the trigger the encounter system listens for).

NPCs skip `update` — `NpcController` calls `begin`/`advance` directly so no NPC step fires the player's move event.

### `EncounterSystem` — roll for a wild battle
Constructed with the map's bush-tile set, the `player_state`, and a `DataLoader`. It **subscribes to `PlayerFinishedMoveEvent`** and, on each landed tile:

1. O(1) set check — is the tile grass? If not, return.
2. Look up the map's table in the cached `data_loader.encounters` (`.get(map_name)` → `None` guard if the map has no data); read its **per-map `encounter_rate`** (falls back to `constants.ENCOUNTER_RATE`). `random() >= rate`? Return.
3. Otherwise weight-pick a species from `table["grass"]`, roll a level, and **publish `BattleEncounterTriggeredEvent`**.

As of 2026-06-25 it reads the **cached** `data_loader.encounters` instead of re-opening `encounters.json` every step (the old `get_enc()` is gone), and the encounter chance is per-map data, not a global constant. Note the explicit `resubscribe()`/`cleanup()` pair and `_subscribed` guard — the overworld re-subscribes it on show and tears it down on hide, so it doesn't fire while off-screen.

### The NPC trio
NPC logic is deliberately split three ways — one reason to change each:

- **`npc_behaviors.py` — *decide*.** `Behavior` subclasses (`IdleBehavior`, `LookAroundBehavior`, `WanderBehavior`) each return a movement **intent dict** (same shape `PlayerInput` produces) or `None`. `make_behavior(properties)` builds one from TMX object props (`behavior`, `wander_radius`, `move_cooldown`). **Add an NPC behavior = one subclass + one `make_behavior` branch** — no other file changes. This is the repo's reference scalability pattern.
- **`npc_controller.py` — *drive + walkability*.** Each frame, for every NPC: if idle, ask its   behavior for an intent and apply it (`turn` or `move` via `MovementSystem.begin`); then `advance` the tween and sync the sprite. It also answers `can_walk(x, y, asking)` — checking map bounds, static collision, the player's cell, and other NPCs' cells. **This is the one file that imports `arcade`** (it uses `get_sprites_at_point` for collision), so it's really overworld glue, not pure logic.
- **`npc_manager.py` — *remember*.** Tracks per-NPC `NPCState` (`has_talked`, `has_fought`, `defeated`, plus arbitrary `custom_flags`). `get_state` lazily creates state on first access.  `load_from_dict`/`save_to_dict` are the save round-trip — this is what `PlayerManager.capture_npc_states` flushes into the save (see `save_manager_report.md`).

### `DialogManager` — pick the right lines
Loads `data/npc_dialog.json` and, given an `npc_id`, returns the dialog list that matches the NPC's current `NPCState` by **priority**: `after_defeat → after_fight → revisit → first_encounter → default → first available → ["..."]`. `get_dialog_type` exposes which branch won; `has_battle_dialog` asks if the NPC has post-fight lines. It depends on `NPCManager` for the state read.

---

## 5. The battle / inventory stack

### `BattleSystem` — the turn engine (344 LOC)
The biggest system, and orchestration-heavy. It owns a `turn_queue`, a `BattleState` enum, pending `exp`, and the trainer party. The flow:

- **`turn(move_index)` / `turn_use_item(item_index)` / `switch_turn()`** build a `turn_queue` of `(actor, move_index, item_index)` tuples, ordered by speed, then call `execute_next_action`.
- **`execute_next_action()`** pops one action, runs `_execute_move` (or `_apply_item_to_pokemon`), clears the queue if anyone hit 0 HP, and returns the message list the view will display.
- **`_execute_move`** is the clean seam: it fetches move data, asks the `BattlePokemon` if it can move (status/PP), calls the **pure** `calculate_damage` (in `core/`, no side effects — now passed `type_chart=self.data_loader.types`, the cached type chart, instead of the calculator reading `types.json` itself), applies the damage + effects, then **publishes `HpChangedEvent`** for the UI bar.
- **`post_turn` / `pokemon_death`** handle end-of-turn status ticks and faints, setting the next `BattleState` (`END`, `TRAINER_SWITCH`, `PLAYER_FAINTED`, …) and publishing `PokemonFaintedEvent`.
- **Decision helpers the view leans on:** `apply_exp_award()` (returns an `ExpGainResult` so the view reacts without mutating models), `add_caught_pokemon()`, `attempt_catch()` (uses the pure `calc_catch_probability`), `has_usable_pokemon()`, `complete_forced_switch()`.
- **`save()`** delegates to `PlayerManager.persist_active_pokemon` — persistence is *not* combat's job, so it's a one-line hand-off to the Facade.

### `BagSystem` — items & pokeballs
Holds references to the player's `items`/`pokeballs` lists. Its highlight is the **effect-dispatch
dict**:

```python
self._effect_appliers   = {EffectType.HEAL: self._apply_heal}      # apply (mutates HP)
self._effect_eligibility = {EffectType.HEAL: self._heal_eligible}  # check (pure, for the UI)
```

`_handle_item_effects` looks up an applier by `effect.type` and calls it; `can_use_item` looks up an **eligibility** check the same way (as of 2026-06-25 it dispatches through `_effect_eligibility` instead of a hardcoded `if effect.type == EffectType.HEAL`). Two parallel dicts because "apply" mutates HP while "check" must stay read-only — the UI greys an item without healing. **Add an effect kind (cure status, boost) = one applier + one eligibility entry, no loop edits**. `use_item` only consumes the item if the effect actually applied (`_apply_heal` returns `False` when the target is full/fainted). `use_pokeball` consumes a ball and returns its `ItemSpecies` for the catch flow. (`ItemEffect.type` is now a typed `EffectType`, parsed at load.)

### `PokemonMenuSystem` — party order
The thinnest logic system: swap helpers over the team list. `confirm_switch(to_index)` swaps a bench Pokémon into the active slot (index 0) unless it's fainted; `move_pokemon`/`start_moving`/ `cancel_moving` drive the drag-to-reorder UI; `move_team_index`/`move_tooltip_index` wrap cursor movement. Its fields are now snake_case (`moving_pokemon_index`, `team_index`, `tooltip_index`) — the plan §4 holdout was converted 2026-06-25. `start_switching` is still dead code.

### `wild_moveset.select_wild_moves` — give wild foes real moves
A pure helper (no class, no arcade): `select_wild_moves(species, level, data_loader)` filters the species `learnset` to moves with `level <= wild's level`, sorts by level, and keeps the **last `MAX_MOVES` (4)** learned — resolving each move's pp via `data_loader.get_move`. Empty/missing learnset falls back to Tackle so a wild is never moveless. `BattleView` calls it when building a wild enemy (replacing the old hardcoded `[tackle]`). Deterministic — same species+level → same moveset; the per-turn *choice* among them is the random part (in `BattleSystem`).

---

## 6. How they connect — the event web

Systems don't call each other directly; they chain through `global_bus` (see `event_system_report.md`). The overworld encounter chain is the clearest example:

```
 player walks
   └─ MovementSystem.update → publish(PlayerFinishedMoveEvent)
        └─ EncounterSystem._on_player_moved   (subscribed)
             └─ publish(BattleEncounterTriggeredEvent)
                  └─ OverworldView   (subscribed) → swap("battle") → GameDirector builds BattleView
                       └─ BattleView constructs BattleSystem
```

`MovementSystem` has never heard of `EncounterSystem`; `EncounterSystem` has never heard of the view. Each knows only its event type. Inside a battle, `BattleSystem` publishes `HpChangedEvent` / `PokemonFaintedEvent` that the battle UI subscribes to for bar/faint animations, while returning `list[str]` messages the view queues into the text box.

The NPC cluster connects differently — by **shared object**, not events: `OverworldView` builds an `NpcController` (given the `MovementSystem` + `player_state`), and `PlayerManager` owns the `NPCManager` that both `DialogManager` and the battle/victory flow read and mutate.

---

## 7. Dependency map (who needs whom)

```
 MovementSystem  ──(no deps)──────────────  drives PlayerMotion / NPC GridMotion
 EncounterSystem ── DataLoader, player_state, bush_tiles
 NpcController   ── MovementSystem, npcs, collision_tiles, player_state   (imports arcade)
 NpcBehavior     ──(no deps)──────────────  returns intent dicts
 NPCManager      ── NPCState model
 DialogManager   ── NPCManager
 BattleSystem    ── PlayerManager, DataLoader, combat_calculator, catch_calculator
 BagSystem       ── PlayerManager, DataLoader
 PokemonMenuSystem ── PlayerManager
```

The pure-math helpers (`combat_calculator`, `catch_calculator`) live in `core/`, not here — systems *orchestrate*; the formulas are side-effect-free functions the systems call.

---

## 8. How to use them

### Drive overworld movement (in the view's `on_update`)
```python
intent = self.player_input.poll(self.keys, self.player_state, self.movement_system)
self.movement_system.update(delta_time, self.player_state, intent)   # publishes the move event
```

### Wire encounters for a map
```python
self.encounter_system = EncounterSystem(bush_tiles, self.player_state, self.data_loader)
# auto-subscribes; call .cleanup() on view hide, .resubscribe() on show
```

### Run a battle turn (from `BattleView`)
```python
messages = self.battle_system.turn(selected_move_index)   # list[str] for the text box
# react to HpChangedEvent / PokemonFaintedEvent in the UI
```

### Use a bag item
```python
if self.bag_system.can_use_item(item_index, pokemon_id):
    self.bag_system.use_item(item_index, pokemon_id)   # consumes only if it applied
```

### Add a new NPC behavior (the scalable path)
1. Subclass `Behavior`, implement `decide(npc, world, dt)` → intent dict or `None`.
2. Add one branch to `make_behavior`.
3. Set `behavior: <name>` (+ params) on the TMX object. No view/controller edits.

### Add a new item effect (same shape)
1. Write `_apply_<kind>(self, pokemon_id, pokemon, max_hp, effect) -> bool` on `BagSystem`.
2. Register it in **both** dicts: `self._effect_appliers[EffectType.<KIND>] = self._apply_<kind>` and `self._effect_eligibility[EffectType.<KIND>] = self._<kind>_eligible`.
3. Add the `EffectType.<KIND>` enum member + the effect to the item's JSON. No loop edits.

---

## 9. Conventions & gotchas

- **Subscribe/unsubscribe in pairs.** Systems that listen (`EncounterSystem`) expose   `resubscribe`/`cleanup` and a `_subscribed` guard; the owning view must call them on show/hide or they fire while off-screen.
- **Systems publish, never navigate.** A system fires an event; the *view* turns it into a `swap`/`overlay`. Keep `window.show_view()` out of `systems/`.
- **Mutate through Facades.** Write party/HP/money via `PlayerManager`, not `save.json`. Persistence is `PlayerManager`'s job (`BattleSystem.save()` is a one-line delegate).
- **`npc_controller` is the arcade exception.** It imports `arcade` for sprite collision; treat it as overworld glue, not pure logic, if you enforce a `systems → no arcade` lint contract.
- **Known debt:** `PokemonMenuSystem` still has dead `start_switching` (camelCase was fixed 2026-06-25); `BattleSystem` carries multiple responsibilities (SRP audit). Documented, not yet split.
