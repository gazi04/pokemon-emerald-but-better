# Pokémon Object Model — How It's Written, How It Works, How It Connects

## 1. The core idea, in one line

There is no single "Pokémon" class. A pokémon is represented by **different objects at different lifetimes**, each owning exactly one concern: what a species *is* (static), what the player *owns* (save), what is *happening in a battle* (runtime), and what is *drawn* (sprite). The whole design is about keeping those four from leaking into each other.

---

## 2. The five layers

```
 Layer 1  Static Data      src/model/static/   "what a species is"     read-only, whole process
 Layer 2  Save State       src/model/save/     "what the player owns"  mutable, whole process
 Layer 3  Battle Runtime   src/model/battle/   "what's happening now"  mutable, one battle
 Layer 4  Presentation     src/entities/       "the pixels"            mutable, one battle
 Layer 5  Wiring           src/core/           owns + hands out 1–4    structural
```

| Layer | Folder | Owner | Lives until | Written by |
|---|---|---|---|---|
| Static | `src/model/static/` | `DataLoader` | process exit | nobody (read-only) |
| Save | `src/model/save/` | `SaveManager` | process exit | `flush_save()` |
| Battle | `src/model/battle/` | `BattleView` | battle ends | `BattleSystem` |
| Presentation | `src/entities/` | `BattleView` | battle ends | `BattleView` |
| Wiring | `src/core/` | `GameDirector` | process exit | n/a |

The **direction rule**: dependencies only point *down* — save may import static, battle may import both, nothing imports up. Two shared foundations sit below everything: `src/enums/` (value vocabulary) and the typed result dataclasses in `src/model/battle/`.

---

## 3. Layer 1 — Static Data (`src/model/static/`)

Plain frozen-ish dataclasses describing a species. Loaded once at startup by `DataLoader` (via `GameDataParser`) from `data/*.json`; never mutated after. Naming convention: **`Species`** for static definition types.

```
PokemonSpecies          (pokemon.py)
├── baseExp, catch_rate, abilities, types
├── evolution: PokemonEvolution | None  (to, levelCap)
├── sprites: SpritePaths (back, front)
├── stats: PokemonStat  (hp, attack, defence, special_attack, special_defence, speed)
└── learnset: list[LearnsetMove]  (move, level)  — wild moveset source, default []

PokemonStat             — also the leveled-stat math lives here:
    scaled(base, level, is_hp)   one canonical formula  (pokemon.py:29)
    max_hp(base_hp, level)       HP gets the +level term
    at_level(level)              returns a fully leveled PokemonStat block

PokemonMove / PokemonMoveEffect  — effect fields are typed enums (Stat/StatusEffect/EffectType),
                                   parsed once by GameDataParser, not per-turn

LearnsetMove (pokemon.py)  — {move, level}; wild_moveset.select_wild_moves picks the last 4
                             learned ≤ the wild's level (Tackle fallback)

ItemSpecies / ItemEffect (item.py)  — ItemEffect.type is a typed EffectType (parsed at load,
                                      mirrors PokemonMoveEffect), not a string
NpcSpecies (npc.py)
Trainer / TrainerPokemon / TrainerPokemonMove  (trainer.py)  ← spec, not save records
```

Two things to note:
- **The stat formula has one home** (`PokemonStat.scaled`), reused by `at_level` and `max_hp` — no duplicated leveling math.
- **Trainers got their own spec type.** `Trainer.party` is `list[TrainerPokemon]`   (`trainer.py:11`) — name/level/moves only. It used to reuse the *save-layer* `PlayerPokemon`, which inverted the dependency direction; that's fixed.

Access is always through `DataLoader.get_pokemon(name)` / `get_move(name)` / `get_item(name)` — systems never read `data/*.json` directly.

---

## 4. Layer 2 — Save State (`src/model/save/`)

What the player owns and has done. Mutable, persisted. `HP` here is "benched HP" — the value written to disk, **not** the battle-live value.

```
PlayerSave              (player.py)
├── pokemon: list[PlayerPokemon]   party (max 6), index 0 = active
├── items / pokeballs: list[ItemStack]   ({name, count}) — one merged stack type
├── seen: list[str]
├── money: int
└── npc_states: list[dict]
    + data mutators:  update_hp / update_move_pp / update_level / add_pokemon /
                      mark_seen / consume_item / consume_pokeball   (player.py:46–99)

PlayerPokemon  (name, hp, level, exp, moves)  + is_fainted property
NPCState       (npc_state.py)  per-NPC flags, to_dict/from_dict round-trip
```

**The mutation door (single owner).** `PlayerSave` owns the actual field writes; `PlayerManager` (Layer 5) is the only production caller and just *orchestrates* — it delegates the write down to `PlayerSave` and adds cross-cutting work (events / flush). There is exactly **one door**, not two parallel ones. Example: `PlayerManager.update_pokemon_hp` → `PlayerSave.update_hp` (`player_manager.py:50`).

---

## 5. Layer 3 — Battle Runtime (`src/model/battle/`)

`BattlePokemon` is **combat-only** state, alive for one battle. This is the most mutable object — HP, PP, stat stages, and status all change turn by turn. It is arcade-free domain logic.

### How it's built — two intent-named constructors over one private `__init__`

```python
BattlePokemon.from_player(
    species, player_pokemon, is_enemy=False
)  # battle_pokemon.py:27
BattlePokemon.from_wild(
    species, name, level, moves, is_enemy=True
)  # battle_pokemon.py:45
```

Both funnel into `_apply(...)` (`battle_pokemon.py:56`), the single build path. `switching_pokemon` (`:152`) reuses `_apply` too, so the object is never built two different ways. This replaced an overloaded 7-param constructor with two mutually-exclusive modes.

### What `_apply` assembles

```
BattlePokemon
├── from species (copied, not referenced):  base_stat, types, evolution, base_exp   (_load_species :105)
├── from the save record:                   name, moves (live PP), current_hp, max_hp
├── progression: Progression                ← level/exp delegated here (see below)
├── runtime state:                          stats, modifiers{Stat:int}, status_effect, sleep_counter
└── source: PlayerPokemon | None            back-pointer to the save object (None for wild)
```

`level` and `exp` are **properties** over `self.progression` (`:85–99`) — combat code reads them naturally, but the curve math lives elsewhere.

### Progression is a separate object

```
Progression             (progression.py)
    exp_needed()  → level ** 3
    exp_yield()   → (base_exp * level) // 7   (granted to the victor on faint)
    exp_ratio()   → UI bar progress
    add_exp(n)    → applies exp, levels up as many times as the curve allows, returns levels gained
    can_evolve() / evolves_to
```

`BattlePokemon.gain_exp` (`:274`) only **reacts** to a level-up reported by `Progression.add_exp`: recompute stats, refresh `max_hp`, heal to full — then returns a typed `ExpGainResult`. The leveling math is not interleaved with combat anymore.

### What the battle object actually does (its methods)

| Method | Role |
|---|---|
| `get_stat(stat)` (`:128`) | stage-modified stat value (`getattr` + stage math; HP read directly via `self.stats.hp`) |
| `take_damage(d)` (`:149`) | the only mutator that touches HP |
| `check_can_move(i)` (`:168`) | status/PP gating before a move; decrements PP; returns `(messages, can_move)` |
| `execute_effects(move, target)` (`:199`) | apply stat-stage / status effects, return messages — dispatches via `_effect_handlers` (`{EffectType.STAT: _apply_stat_effect, EffectType.STATUS_CONDITION: _apply_status_effect}`), not an inline if/else |
| `after_a_turn()` (`:251`) | post-turn tick (poison damage) |
| `sync_from_source()` (`:264`) | pull hp/level/exp back from `source` |

---

## 6. Layer 4 — Presentation (`src/entities/pokemon_sprites.py`)

`PokemonSprite` is a pure `arcade.Sprite` — texture + position, nothing else. It does **not** own the `BattlePokemon`; `BattleView` holds the two side by side.

```
BattleView
├── your_battle / enemy_battle : BattlePokemon   (logic)
├── your_sprite / enemy_sprite : PokemonSprite   (pixels)
└── battle_system              : BattleSystem    (receives the BattlePokemon objects, not sprites)
```

Sprite + logic are kept in lockstep through **one** entry point, `BattleView.set_enemy(name, level, moves)`, which does all three coordinated steps at once (new `BattlePokemon`, swap sprite texture via `set_new_texture`, repoint `battle_system.enemy_pokemon`) — so a trainer sending its next pokémon can't desync them.

---

## 7. Layer 5 — Wiring (`src/core/`)

```
DataLoader     → Layer-1 dicts; get_pokemon / get_move / get_item
SaveManager    → player: PlayerSave (Layer 2); flush_save() (atomic, with backup fallback)
PlayerManager  → same PlayerSave; the single mutation door (delegates writes to PlayerSave),
                 plus add_money/heal_team/capture_npc_states/… (player_manager.py)
```

```
GameDirector
├── DataLoader      ─────────────► BattleSystem, OverworldView, every view
├── SaveManager
└── PlayerManager   ─────────────► BattleSystem, BagSystem, PokemonMenuSystem

OverworldView
└── PlayerMotion (owns it; passed to flush_save at save time)
```

---

## 8. The lifecycle of one pokémon's HP (the sync contract)

This is the spine of the whole model — how the *same* pokémon's HP moves across layers:

```
data/pokemon.json ──load──► PokemonSpecies.stats        (base, never changes)
data/save.json    ──load──► PlayerPokemon.hp            (benched HP)
                                  │ battle start: read into
                                  ▼
                           BattlePokemon.current_hp      (the only value that changes in battle)
                                  │  faint? → PlayerManager.update_pokemon_hp (single door)
                                  │  battle end: BattleSystem.save() copies hp/pp/level/exp back
                                  ▼
                           PlayerPokemon (source)
                                  │ flush_save()
                                  ▼
                             data/save.json
```

Rules that keep it correct:
- During battle, **only `BattlePokemon.current_hp` changes**; `PlayerPokemon.hp` is untouched — *except* a faint, which persists the fainted mon's HP through `PlayerManager.update_pokemon_hp` (because `save()` only writes the *active* pokémon).
- `flush_save()` must run **after** `BattleSystem.save()` syncs back, or HP/PP is lost. Enforced by `GameDirector` only flushing on the overworld save event, post-battle.

---

## 9. Shared foundations

### Enums (`src/enums/`) — value vocabulary, imported *down* by every layer

```
Stat          HP / ATTACK / DEFENCE / SPECIAL_ATTACK / SPECIAL_DEFENCE / SPEED / ACCURACY / EVASION / CRITS
StatusEffect  NONE / POISON / PARALYSIS / SLEEP / BURN / FREEZE
EffectType    STAT / STATUS_CONDITION / HEAL / CATCH
BattleState   INTRO / CURRENTLY_TURN / … / END
```

All are `StrEnum`, so JSON-parsed strings compare transparently while code gets autocomplete + exhaustiveness. They replaced the former raw-string status/stat/effect state.

### Typed result dataclasses (`src/model/battle/`)

```
CombatResult   (damage, messages, is_miss)              ← calculate_damage()
ExpGainResult  (leveled_up, stats_before, stats_after,  ← BattlePokemon.gain_exp()
                evolved, evolves_to)
```

Both replaced stringly-keyed dicts (`result["isLeveledUp"]`) — no silent typo'd-key bugs.

### Transient motion (`src/model/motion/`)

`PlayerMotion` (owned by `OverworldView`, mutated 60×/s by `MovementSystem`) and `GridMotion` (NPC interpolation). Not part of the save schema — at flush time only `map_name`/`direction`/ `grid_x`/`grid_y` are extracted manually into the save dict.

---

## 10. Component connection map

```
                         ┌───────────────────────────────┐
                         │          GameDirector          │
                         │  owns DataLoader / SaveManager  │
                         │  / PlayerManager; injects them  │
                         └───┬─────────────┬──────────┬────┘
              DataLoader     │   PlayerMgr  │          │ SaveManager
        ┌──────────────────┘              └───────┐  └──────────────┐
        ▼                                          ▼                 ▼
┌────────────────┐   get_pokemon/move    ┌──────────────────┐  ┌──────────────┐
│  Static Layer  │◄──────────────────────│   Systems        │  │  PlayerSave  │
│  PokemonSpecies│                       │  BattleSystem     │  │  (save state)│
│  …Species/Move │                       │  BagSystem        │  │  ▲ mutators  │
└───────┬────────┘                       │  PokemonMenuSys   │──┘  (one door)  │
        │ species data                   └────────┬──────────┘                 │
        │                  build via               │ reads/writes               │
        ▼          from_player / from_wild         ▼                            │
┌──────────────────────────┐   source ptr  ┌────────────────┐                  │
│   BattlePokemon (battle)  │──────────────►│ PlayerPokemon  │──────────────────┘
│   + Progression           │   sync back    │  (in PlayerSave)│   flush_save → save.json
└───────────┬───────────────┘               └────────────────┘
            │ held beside (not owned)
            ▼
   ┌──────────────────┐
   │  PokemonSprite   │   BattleView.set_enemy() keeps the two in lockstep
   └──────────────────┘
```

---

## 11. Strengths and current ceiling

**Strengths**
- One concern per object; each has a clear owner and lifetime.
- Dependencies point one way (save→static, battle→both); a trainer's roster is a spec, not a save record.
- Battle logic is arcade-free → unit-testable without a window (151 tests pass).
- Stringly-typed state is gone (enums); dict-returns are gone (typed results); the stat formula and the object-build path each have a single home.
- One mutation door (`PlayerManager` → `PlayerSave`); one sprite/logic sync point (`set_enemy`).

**Ceiling (documented, deferred)**
- **Save-format / "real depth" milestone is not done.** IVs, EVs, natures, abilities, held items   are not yet persisted fields on `PlayerPokemon`. Adding them changes the `save.json` schema (serializer needs defaults so old saves load) and the stat formula (`PokemonStat.scaled`), which touches every stat test. Planned as its own milestone, not a cleanup.
- A few UI-internal camelCase handles remain (pure presentation; cosmetic).
- `data_loader.get_*()` returns `Optional` and several battle call sites assume non-None — a known latent None-safety cleanup, separate from this model.

---

## 12. Usage guide

### 12.1 Reading a pokémon's data — pick the right layer

| You want… | Read from | Not from |
|---|---|---|
| Base/species facts (types, base stats, evolution) | `DataLoader.get_pokemon(name)` → `PokemonSpecies` | a `BattlePokemon` copy |
| What the player owns (party, benched HP, money) | `PlayerManager` getters → `PlayerSave` | `save_manager.player` directly |
| Live in-battle HP / status / stat stages | `BattlePokemon` (`current_hp`, `status_effect`, `get_stat`) | `PlayerPokemon.hp` (that's benched) |
| Level / exp during battle | `BattlePokemon.level` / `.exp` (properties over `Progression`) | recompute by hand |

### 12.2 Building a battle pokémon

```python
species = data_loader.get_pokemon(player_pokemon.name)  # Layer 1
mine = BattlePokemon.from_player(species, player_pokemon)  # owned mon
foe = BattlePokemon.from_wild(species, name, level, moves)  # wild/trainer mon
```

Never call `BattlePokemon(...)` directly — use the classmethods (they name the intent and fill the right fields).

### 12.3 Mutating save data — always through the manager

```python
# GOOD — single door; manager delegates to PlayerSave and handles flush/events
player_manager.update_pokemon_hp("mudkip", new_hp)
player_manager.consume_pokeball("pokeball")
player_manager.add_money(500)

# BAD — never write PlayerSave fields straight from a system
save_manager.player.pokemon[0].hp = new_hp  # bypasses the door → desync risk
```

### 12.4 Swapping the enemy mid-battle — one call

```python
# GOOD — set_enemy does all three steps (model + sprite + system pointer)
self.set_enemy(next.name, next.level, next.moves)

# BAD — three manual mutations; miss one → sprite/logic/system desync
self.enemy_battle = BattlePokemon.from_wild(...)
self.enemy_sprite.texture = arcade.load_texture(...)
self.battle_system.enemy_pokemon = self.enemy_battle
```

### 12.5 Common bugs from mixing layers

- Writing `PlayerPokemon.hp` directly in battle → overworld HP display desyncs. Use   `BattlePokemon.current_hp`; the one legit faint-time write goes through   `PlayerManager.update_pokemon_hp`.
- Holding a `BattlePokemon` reference after the battle → stale object (it's discarded on   `BattleView` close).
- Calling `flush_save()` before `BattleSystem.save()` → HP/PP lost on disk.
- Adding a new persisted field to `PlayerPokemon` without a serializer default → old saves fail to load (see the deferred save-format milestone).
