# Project Analysis: Pokémon Emerald But BETTER

**Date**: 2026-05-24  
**Version**: 0.1.0  
**Language**: Python 3.14+  
**Framework**: Arcade 3.3.3+  
**Dependency Manager**: uv  
**Total Source Lines**: ~3,500 across 27 Python files (src/ + root scripts + data/config.py)

---

## 1. Executive Summary

Pokémon Emerald But BETTER is a from-scratch Python remake of the 2004 Game Boy Advance classic *Pokémon Emerald* (3rd generation). It implements tile-based overworld exploration with camera interpolation, random wild Pokémon encounters, and a turn-based battle system that models damage calculation, type effectiveness, STAB, critical hits, status effects, stat modifiers, evolution sequences, and an inventory/bag system.

The codebase is undergoing (or has undergone) a migration from monolithic "God classes" toward a modular architecture. The project currently sits in a state where the old dataclass-based implementation is the active runtime, while traces of a newer Pydantic v2–based refactor appear to have existed but are no longer present in the current code tree.

---

## 2. Project Structure

```
pokemon-emerald/
├── main.py                          # Entry point — creates Arcade window, launches OverworldView
├── debug_ui.py                      # Standalone debug script for BattleUiManager testing
├── parse_test.py                    # Standalone script for layout parser testing
├── test_label.py                    # Standalone script for UILabel sizing tests
├── pyproject.toml                   # Project metadata, dependencies (arcade, pydantic), dev tools
├── uv.lock                          # Lock file for uv dependency resolution
├── README.md                        # Project documentation
│
├── data/                            # Static data files + configuration
│   ├── config.json                  # Window, audio, controls, game settings
│   ├── config.py                    # Pydantic BaseModel validators for config
│   ├── player.json                  # Save file — player's Pokémon, items, pokeballs
│   ├── pokemon.json                 # 12 Pokémon species: stats, types, sprites, evolutions
│   ├── moves.json                   # Move definitions: type, power, accuracy, PP, effects
│   ├── items.json                   # Item definitions: potion (heal), pokeball (catch)
│   ├── encounters.json              # Wild Pokémon encounter tables per map
│   └── types.json                   # 18-type effectiveness matrix
│
├── assets/
│   ├── fonts/
│   │   └── pokemon-emerald.otf      # Custom pixel font for UI
│   ├── map/
│   │   ├── littleroot_town.tmx      # Starting town map (Tiled format)
│   │   ├── test.tmx                 # Additional test map
│   │   ├── tiles.png / Tiles.tsx    # Tile spritesheet + Tiled tileset
│   │   └── Interior Tilesets.*      # Interior/indoor tiles
│   ├── sound/
│   │   └── .gitkeep                 # Placeholder (no audio implemented yet)
│   ├── sprite/
│   │   ├── player/
│   │   │   ├── brendan.png          # Full player spritesheet
│   │   │   ├── idle/                # 3 idle textures (down, up, left)
│   │   │   └── walk_anim/           # 6 walk animation frames (2 per direction)
│   │   └── pokemon/
│   │       ├── front/               # 6 front sprites (for enemy display)
│   │       ├── back/                # 6 back sprites (for player display)
│   │       └── question_mark.png    # Unknown Pokémon placeholder
│   └── ui/
│       ├── *.tmx                    # 5 Tiled UI layout files (bag, battle, evolving, menu, pokemon menu)
│       └── sprites/                 # 27 UI element textures (buttons, HP bars, dialog boxes, etc.)
│
├── src/
│   ├── constants.py                 # 13 game constants
│   ├── util.py                      # Utility functions: config loading, type multiplier calc
│   │
│   ├── core/                        # Game systems and data management
│   │   ├── gameContext.py           # Singleton global instances (saveManager, dataLoader)
│   │   ├── dataLoader.py            # Loads pokemon.json, moves.json, items.json into dataclass models
│   │   ├── saveManager.py           # In-memory player state + disk flush
│   │   ├── battleSystem.py          # Turn queue, action execution, EXP gain, death handling
│   │   ├── bagSystem.py             # Inventory item usage and validation
│   │   └── pokemonMenuSystem.py     # Team reordering, selection management
│   │
│   ├── model/                       # Data models (dataclass-based)
│   │   ├── player.py                # PlayerProfile, PlayerState, PlayerPokemon, Item, Pokeball
│   │   ├── pokemon.py               # PokemonProfile, PokemonStat, PokemonMove, Evolution, etc.
│   │   └── item.py                  # Item, ItemEffect
│   │
│   ├── entities/                    # Visible game objects (arcade.Sprite subclasses)
│   │   ├── player_sprite.py         # PlayerSprite — idle/walk animation, 4-direction textures
│   │   ├── pokemonSprites.py        # Pokemon arcade.Sprite — front/back sprites, wraps PokemonBattle
│   │   ├── pokemonBattle.py         # PokemonBattle — battle logic (damage, stats, effects, leveling)
│   │   └── __init__.py              # Exports PlayerSprite
│   │
│   ├── controllers/                 # Input translation layer
│   │   └── player_input.py          # PlayerInput — keyboard → semantic intents (move, turn, transition)
│   │
│   ├── systems/                     # Game rule systems
│   │   ├── movement_system.py       # MovementSystem — tile-based lerp movement, event emission
│   │   └── encounter_system.py      # EncounterSystem — grass detection, random encounter generation
│   │
│   ├── states/                      # Arcade Views (game screens)
│   │   ├── overworld_view.py        # OverworldView — main exploration screen
│   │   ├── battleView.py            # BattleView — turn-based battle screen
│   │   ├── bagView.py               # BagView — inventory browsing screen
│   │   ├── menuView.py              # MenuView — pause menu overlay
│   │   ├── pokemonMenuView.py       # PokemonMenuView — team management screen
│   │   └── evolvingView.py          # EvolvingView — evolution animation screen
│   │
│   └── ui/                          # UI rendering layer
│       ├── layout_parser.py         # parse_battle_layout — extracts bounds from Tiled TMX
│       ├── battle_ui_manager.py     # BattleUiManager — orchestrates all battle UI components
│       ├── bagUi.py                 # BagUI — bag/items screen rendering
│       ├── menuUi.py                # MenuUi — pause menu rendering
│       ├── pokemonMenuUi.py         # PokemonMenuUi — team roster UI with HP bars
│       └── components/
│           ├── typewriter_message_box.py  # TypewriterMessageBox — animated text display
│           └── battle_menu_panel.py       # BattleMenuPanel — fight/bag/pokemon/run + move buttons
│
├── docs/                            # Documentation
│   ├── project-analysis.md          # This file
│   ├── bug-report.md                # Known bugs and issues
│   ├── code-quality-analysis.md     # Code quality assessment
│   ├── game-status-report.md        # Current game state
│   ├── refactoring_plan.md          # Architecture migration plan
│   ├── roadmaps.md                  # Development roadmap
│   ├── event_system_implementation.md
│   └── architecture_problems/       # Architecture issue analysis
│
└── .github/workflows/lint.yaml      # CI: Ruff format + lint on push to main
```

---

## 3. Code Architecture

### 3.1 Overall Architecture Pattern

The project follows a **modified MVC (Model-View-Controller) architecture** adapted for Arcade's View-based game loop:

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| **Model** | `src/model/`, `data/` | Pure data structures (dataclasses), JSON data files, Pydantic config |
| **View** | `src/states/`, `src/ui/` | Arcade `View` subclasses + UI component rendering |
| **Controller** | `src/controllers/`, parts of `src/systems/` | Input processing, intent generation |
| **Logic/System** | `src/core/`, `src/systems/` | Game rules, state mutations, battle engine |
| **Entity** | `src/entities/` | Visual game objects sprites |

### 3.2 Data Flow

```
┌──────────────┐    keyboard    ┌────────────────┐
│   Arcade      │──────────────→│  PlayerInput    │
│  Window       │               │  (Controller)   │
│               │               │  process_input  │
│  on_key_press │               └────────┬───────┘
│  on_update    │                        │ intent dict
│  on_draw      │                        ↓
│               │               ┌────────────────┐
│               │               │ OverworldView   │
│               │               │ (State/View)    │
│               │               │                 │
│               │               │  intent → system│
│               │               │  systems → state│
│               │               │  state → sprite │
│               │               └───┬─────────┬───┘
│               │                   │         │
│               │         events[]  │         │ transition
│               │                   ↓         │
│               │           ┌───────────┐     │
│               │           │ Encounter  │     │
│               │           │ System     │     │
│               │           └─────┬─────┘     │
│               │                 │           │
│               │           encounter?        │
│               │                 ↓           │
│               │           ┌───────────┐     │
│               │           │ BattleView │←───┘
│               │           │ (State)    │
│               │           │            │
│               │           │ BattleSys  │
│               │           │ BattleUi   │
│               │           │ Pokemon    │
│               │           └───────────┘
└──────────────┘
```

### 3.3 Runtime Initialization Sequence

1. **`main.py`**: Creates `arcade.Window(800×600)`, then instantiates and shows `OverworldView`.
2. **`OverworldView.__init__()`**: Sets pixelated texture filtering, loads the Pokémon Emerald font, initializes 5 modules:
   - `PlayerState` (data model)
   - `PlayerInput` (controller)
   - `MovementSystem` (logic)
   - `EncounterSystem` (logic)
   - `PlayerSprite` (entity)
   - Loads the Tiled tilemap, sets up camera, reads player spawn position from the map's "position" layer.
3. **`gameContext.py`**: On first import, instantiates `SaveManager` (reads `data/player.json`) and `DataLoader` (reads `data/pokemon.json`, `moves.json`, `items.json`). These are global singletons.

### 3.4 Overworld Game Loop (`on_update`)

```
1. Camera interpolation (lerp toward player)
2. PlayerInput.process_input()
   → Returns None (no input) or intent dict:
     {type: "move", target_x, target_y}
     {type: "turn", direction}
     {type: "transition", map, x, y}
3. If transition intent → load new map tilemap, set player position
4. MovementSystem.update(delta_time, player_state, intent)
   → Starts lerp if move intent and not already moving
   → Updates pixel position via lerp
   → Emits "finished_moving" event when tile reached
5. PlayerSprite.sync_with_state(player_state)
   → Sets texture based on direction, moving flag, progress
6. EncounterSystem.check_encounter()
   → If on a "bush" tile and random < 15% → returns encounter data
7. If encounter → BattleView transition with flicker animation
```

### 3.5 Battle System Flow

```
BattleView.__init__()
├── Creates PokemonBattle instance for player's lead Pokémon
├── Creates PokemonBattle instance for wild enemy Pokémon
│   (hardcoded to know only "Tackle" with 35 PP)
├── Creates BattleSystem(yourPokemon, enemyPokemon)
├── Creates BattleUiManager
├── Loads UI layout from battleUiDesign.tmx via layout_parser
├── Builds all UI widgets (backgrounds, platforms, HP widgets, labels)
├── Sets up TypewriterMessageBox and BattleMenuPanel components
├── Initiates slide-in transition animation
│   (player's side slides from right, enemy's from left)
└── Queues intro messages

During battle:
  Player selects "Fight" → move menu shown
  Selects a move → BattleSystem.turn(moveIndex)
    → Speed comparison determines turn order
    → Turn queue: [("player", idx), ("enemy", idx)]
    → executeNextAction() pops queue, runs useMove()
  
  Player selects "Bag" → BagView overlays, item usage routes back
  Player selects "Pokemon" → PokemonMenuView overlays
  Player selects "Run" → return to overworld

  After both actions:
    → postTurn() checks for fainted Pokémon
    → Status effects applied (poison damage)
    → If enemy fainted: EXP gain → level up check → evolution check
    → If player fainted: black out, return to overworld
    → saveManager.flushToDisk() writes state to player.json
```

### 3.6 Damage Calculation Formula

The damage formula in `pokemonBattle.py:154-159` follows the Generation III standard:

```
damage = (((2 * level / 5 + 1) * movePower * attackStat / defenseStat) / 50 + 2)
         × STAB × typeMultiplier × critMultiplier
```

Where:
- **STAB** (Same-Type Attack Bonus): 1.5× if move type matches a Pokémon's type
- **Type multiplier**: Read from `types.json` matrix (0.0, 0.5, 1.0, 2.0)
- **Critical hit**: Base 1/16 chance per tier, deals 2× damage, ignores stat stage modifiers on defense
- **Stat stages**: -6 to +6 scale, formula: (2 + stage) / 2 for positive, 2 / (2 + |stage|) for negative

---

## 4. Component Deep Dive

### 4.1 Core Systems

#### `gameContext.py` (5 lines)
A simple module that creates global singleton instances:
- `saveManager = SaveManager()` — in-memory player state
- `dataLoader = DataLoader()` — Pokémon/move/item database cache

Both are imported by every module that needs game data.

#### `dataLoader.py` (61 lines)
Reads JSON data files at startup into Python dataclass models:
- `_loadPokemons()` → `dict[str, PokemonProfile]`
- `_loadMoves()` → `dict[str, PokemonMove]`
- `_loadItems()` → `dict[str, Item]`

Provides `getPokemon()`, `getMove()`, `getItem()` accessors. **Note**: `types.json` and `encounters.json` are NOT loaded here — they're read via `util.py` functions on every call.

#### `saveManager.py` (122 lines)
- `loadData()` reads `data/player.json` and constructs `PlayerProfile`
- `getPokemon(id)` retrieves a `PlayerPokemon` by name
- `updateHp()`, `updateMove()`, `updateLevel()` mutate in-memory state
- `flushToDisk()` serializes back to `player.json`
- **Key insight**: All updates are in-memory only; disk flush must be called explicitly

#### `battleSystem.py` (125 lines)
- **Turn queue**: Speed comparison determines who moves first; actions queued as `(actor, moveIndex, itemIndex)` tuples
- **executeNextAction()**: Pops queue, calls `useMove()` or `_applyItemToPokemon()`
- **postTurn()**: Checks fainted status, applies post-turn effects (poison), returns to "waiting" or "end" state
- **save()**: Syncs HP, PP, level, and evolution state to `SaveManager`
- **Battle states**: `"intro"` → `"currently turn"` → `"post turn"` → `"waiting"` → `"end"`

#### `bagSystem.py` (66 lines)
- Wraps `saveManager.player.items` and `player.pokeballs`
- `useItem(index, pokemonId)`: Applies item effects (currently only "heal"), decrements count
- `canUseItem()`: Validates item usability
- HP calculation uses the same formula as `PokemonBattle`:
  `maxHp = ((2 * baseStat.hp * level) // 100) + 5 + level`

#### `pokemonMenuSystem.py` (37 lines)
- Manages team roster state: selection index, tooltip index
- `movePokemon(to)`: Swaps team positions (reordering)
- Wraps `saveManager.player.pokemon`

### 4.2 Entity Layer

#### `player_sprite.py` (58 lines)
- `arcade.Sprite` subclass at 1.9× scale
- 4-direction idle textures (up/down/left/right)
- 4-frame walk animations per direction (walk1 → idle → walk2 → idle)
- `sync_with_state(PlayerState)`: Sets texture based on direction, moving flag, and animation progress

#### `pokemonSprites.py` (33 lines)
- `arcade.Sprite` subclass at 3.0× scale
- Selects front (enemy) or back (player) sprite from `PokemonProfile.sprites`
- Creates and wraps a `PokemonBattle` instance
- Positions: enemy at (580, 400), player at (210, bottom=168)

#### `pokemonBattle.py` (298 lines) — Core Battle Logic
This is the most complex class in the codebase:

**Stat Calculation** (Gen III formula):
```
HP:      ((2 * base * level) // 100) + 5 + level
Others:  ((2 * base * level) // 100) + 5
```

**Stat Modifier System**:
- Tracks 7 modifier stages (accuracy, evasion, crits, attack, defense, special attack, special defense, speed)
- Stage range: -6 to +6
- Positive: `(2 + stage) / 2` multiplier
- Negative: `2 / (2 + |stage|)` multiplier

**Move Execution Pipeline**:
1. Status check: paralysis (25% full paralysis), sleep (counter decrement)
2. PP check: reject if 0
3. Accuracy check: final accuracy = base accuracy × stage multiplier
4. Damage calculation (see 3.6)
5. Effect execution: stat changes or status conditions

**Status Conditions**:
- `sleep`: Random 2-5 turn counter, prevents action
- `paralyzed`: 25% full paralysis chance, speed halved
- `poison`: Post-turn damage = `maxHp // 12.5` per turn

**Leveling & Evolution**:
- EXP formula: `baseExp * level / 7` per KO
- Level-up: `expNeeded = level^3`
- Evolution: checked when `evolution.levelCap == level`

### 4.3 State Layer (Arcade Views)

#### `OverworldView` (152 lines)
The main game screen. Owns the composition of:
- `PlayerState` (data)
- `PlayerInput` (controller)
- `MovementSystem` (system)
- `EncounterSystem` (system)
- `PlayerSprite` (entity)
- `arcade.Camera2D` with lerp following
- `arcade.Scene` from Tiled tilemap (collision, bush, transition layers)

**Transition effect**: Battle start uses a flicker animation with configurable interval and max duration.

#### `BattleView` (203 lines)
Orchestrates the battle. Key methods:
- `startTurn(index)`: Player used a move → `battleSystem.turn()` → queue messages
- `whatHappendAfterText()`: Called after dialog text finishes:
  - Turn in progress → execute next action
  - Waiting → schedule return to main menu
  - Battle end → process EXP gain, level up, evolution, or return to overworld
- `moveHover(index)`: Updates move info panel (type, PP) on cursor hover

#### `BagView` (112 lines)
- Scrollable inventory list with visual cursor
- Two sections: Items and Pokéballs (switched with left/right)
- Item use routes to `PokemonMenuView` for target selection
- Max 10 visible items (`MAX_VISIBLE_ITEMS` constant)

#### `EvolvingView` (177 lines)
- Full-screen evolution animation sequence:
  1. Message "What? Pokémon is evolving!" appears (typewriter)
  2. Background fades out
  3. Pulsing sprite animation between old/new forms
  4. Pulse speed accelerates until evolution completes
  5. Background fades in
  6. "Congratulations! It evolved!" message appears
  7. Returns to overworld after 1.5 seconds

#### `PokemonMenuView` (97 lines)
- Team roster navigation with tooltip options
- In battle context: "Use" item on selected Pokémon
- In overworld context: "Move" (reorder) or "Info" options

#### `MenuView` (53 lines)
- Simple overlay menu: Pokémon, Bag, (Save — placeholder)
- Draws overworld scene underneath as dimmed background

### 4.4 UI Layer

#### `BattleUiManager` (217 lines)
Central orchestrator for all battle UI components:

1. **Static graphics** (from `battleUiDesign.tmx`):
   - Background, player/enemy platforms, HP widgets
   - Name/level labels, dialog box background
   
2. **Components**: `TypewriterMessageBox` + `BattleMenuPanel`

3. **Modes**: `"main"` (fight/bag/pokemon/run), `"moves"` (move selection), `"dialog"` (text display)

4. **Slide-in transition**: On battle start, all player-side widgets slide from right, enemy-side from left at speed 7 pixels/frame

5. **HP/EXP bar rendering**: Custom-drawn (not sprite-based) using `arcade.draw_lrbt_rectangle_filled`:
   - Green > 50%, Gold 20-50%, Red < 20%

#### `layout_parser.py` (29 lines)
- Reads Tiled TMX file for UI layouts
- Converts Tiled coordinates (top-left origin) to Arcade coordinates
- Returns a flat dictionary of `{name: {x, y, w, h}}` bounds

#### `TypewriterMessageBox` (79 lines)
- Queues messages for sequential display
- Character-by-character text reveal at `TEXT_DELAY` (0.03s) interval
- 1.5-second pause between messages
- Callback invoked when all messages are consumed

#### `BattleMenuPanel` (141 lines)
- Two sub-menus: main (4 buttons) and moves (4 move buttons)
- Cursor rendering as "▶" character
- Move info display (type label, current/max PP)

#### `PokemonMenuUi` (314 lines)
- 6-slot team roster display with pokeball icons
- HP bars, level text, name text per slot
- Selection highlighting with alternate textures (selected vs unselected)
- Tooltip overlay for actions (Use/Info or Move/Info)

### 4.5 Data Models

All models use Python `dataclass` with manual JSON-to-object conversion in `DataLoader` and `SaveManager`.

**`model/player.py`**:
- `PlayerState` — 15-field dataclass tracking all runtime player state (position, direction, movement progress, map name). This is the single source of truth for the overworld.
- `PlayerProfile` — persistent player data (Pokémon team, items, pokeballs)
- `PlayerPokemon` — per-Pokémon runtime state (name, hp, level, exp, moves)
- `PlayerPokemonMove` — move name + remaining PP

**`model/pokemon.py`**:
- `PokemonProfile` — base species data (stats, types, abilities, sprites, evolution, base EXP)
- `PokemonStat` — 6 IV-like base stats
- `PokemonMove` — move data (category, type, power, accuracy, PP, effects)
- `PokemonMoveEffect` — effect instructions (target, type, stat/condition/change/chance)
- `PokemonSprites` — front/back sprite paths
- `PokemonEvolution` — evolution target + level cap

**`model/item.py`**:
- `Item` — description, price, effects list
- `ItemEffect` — type (heal/catch), amount, catchRate

**`data/config.py`** (Pydantic v2):
- `WindowConfig`, `AudioConfig`, `ControlsConfig`, `GameConfig`
- `Config` (composite) with `Config.load()` classmethod using `model_validate`

---

## 5. Configuration & Data Files

### `data/config.json`
```
Window: 800×600, title "Pokemon Emerald But BETTER", not fullscreen
Audio:  music_volume 0.85, sound_volume 1.0, battle_music 0.9
Controls: Arrow keys, Z=interact, X=cancel/menu, TAB=bag
Game:   starting_map=littleroot_town.tmx, battle_style=set
```

### `data/pokemon.json`
12 Pokémon defined (6 Hoenn natives + 6 evolutions/starter variants):
- **Starters**: Treecko, Torchic (→ Combusken at L16), Mudkip
- **Wild**: Poochyena, Zigzagoon, Wurmple, Lotad, Seedot, Ralts
- **No data**: Sprites don't exist for all defined Pokémon (only 6 front + 6 back sprites found)

### `data/moves.json`
18 moves defined including:
- **Physical**: Tackle (40bp), Close Combat (120bp, defense drop), Rock Smash, Mega Drain, Absorb
- **Status**: Growl (attack -1), Dragon Dance (attack +1, speed +1), Tail Whip (defense -1), Thunder Wave (paralyze), Toxic (poison), Hypnosis (sleep)
- **Special**: Ember, Water Gun, Confusion, Psychic

### `data/types.json`
Complete 18-type effectiveness matrix (Gen III + Fairy), 242 entries.

---

## 6. Features Implemented

### Overworld
- [x] Tile-based map navigation with strict collision detection
- [x] Camera interpolation (lerp speed = 0.2)
- [x] Map transitions via trigger tiles (doorways, map borders)
- [x] Tall grass with 15% wild encounter chance per step
- [x] Player animations: 4-direction idle + walk cycles (2 frames each)
- [x] Battle start flicker/transition animation

### Battle System
- [x] Turn-based loop with speed-determined turn order
- [x] Gen III damage formula: STAB, type effectiveness, critical hits
- [x] 18-type effectiveness matrix with super/not very/no effect messages
- [x] Stat modifier system (6 stages ±6) with appropriate adjective messages
- [x] Status conditions: Sleep (2-5 turns), Paralysis (25% + speed halved), Poison (tick damage)
- [x] Move PP tracking and "no PP left" handling
- [x] Accuracy/evasion stage modifiers
- [x] Wild Pokémon encounters with weighted probability
- [x] EXP gain and level-up system (cubic: level³)
- [x] Evolution sequence with animated sprite pulse transition
- [x] Slide-in UI animation on battle start
- [x] Typewriter text effect for battle messages

### Inventory
- [x] Bag with Items and Pokéballs sections
- [x] Scrollable inventory list (10 visible items)
- [x] Item usage in battle (healing through Pokémon selection)
- [x] Item descriptions on hover

### Team Management
- [x] Pokémon roster display with HP bars, levels, sprites
- [x] Pokémon reordering (move up/down in party)
- [x] In-battle Pokémon selection for item usage

### UI/UX
- [x] Custom pixel font (Pokémon Emerald)
- [x] Tiled-based UI layouts with TMX parsing
- [x] Pause menu accessible with TAB
- [x] Pixelated texture rendering (nearest-neighbor)

---

## 7. Known Gaps & Missing Features

| Feature | Status | Notes |
|---------|--------|-------|
| Pokémon Centers (healing) | ❌ | No healing NPCs or buildings |
| Poké Marts (item shops) | ❌ | No shops to buy items |
| Trainer battles | ❌ | No NPC trainers; wild encounters only |
| Gym battles / Badges | ❌ | No progression system |
| Pokémon switching in battle | ❌ | Only lead Pokémon used |
| Catching Pokémon | ❌ | Pokéballs exist in inventory but catch isn't implemented |
| Sound / Music | ❌ | `assets/sound/` is empty |
| Save/Load UI | ❌ | Auto-saves on battle end only |
| Multiple maps | ⚠️ | Only 1 real map + 1 test map |
| Limited move pool | ⚠️ | Wild Pokémon hardcoded to "Tackle" only |
| No held items | ❌ | Not present in data |
| No Abilities | ❌ | Defined in data but not implemented |
| No breeding | ❌ | Not present |
| No battle animations | ❌ | Static sprites only |
| No nicknames | ❌ | Pokémon use species names |
| No bag sorting | ❌ | Items display in insertion order |
| No dialogue system | ❌ | No NPC interaction framework |
| No weather | ❌ | Not implemented |
| No double battles | ❌ | Not implemented |

---

## 8. Dependency Graph

```
main.py
└── src.states.overworld_view ───────────────────────────────────────────┐
    ├── src.states.battleView ───────────────────────────────────────────┤
    │   ├── src.entities.pokemonSprites                                  │
    │   │   └── src.entities.pokemonBattle ──────────────────────────────┤
    │   │       ├── src.util (calculateMultiplier)                       │
    │   │       ├── src.core.gameContext (dataLoader)                    │
    │   │       └── src.model.pokemon                                    │
    │   ├── src.core.battleSystem ───────────────────────────────────────┤
    │   │   └── src.core.gameContext (saveManager, dataLoader)           │
    │   ├── src.ui.battle_ui_manager ────────────────────────────────────┤
    │   │   ├── src.ui.layout_parser                                     │
    │   │   ├── src.ui.components.typewriter_message_box                 │
    │   │   └── src.ui.components.battle_menu_panel                      │
    │   ├── src.states.evolvingView                                      │
    │   ├── src.states.bagView ──────────────────────────────────────────┤
    │   │   ├── src.ui.bagUi                                             │
    │   │   ├── src.core.bagSystem                                       │
    │   │   └── src.states.pokemonMenuView                               │
    │   └── src.states.pokemonMenuView                                   │
    │       ├── src.ui.pokemonMenuUi                                     │
    │       └── src.core.pokemonMenuSystem                               │
    ├── src.controllers.player_input                                     │
    ├── src.systems.movement_system                                      │
    ├── src.systems.encounter_system                                     │
    │   └── src.util (getEnc)                                            │
    └── src.entities.player_sprite                                       │
                                                                         │
data/ ───────────────────────────────────────────────────────────────────┘
├── config.json ──→ data.config.py (Pydantic) ──→ OverworldView etc.
├── player.json ──→ src.core.saveManager
├── pokemon.json ──→ src.core.dataLoader
├── moves.json ────→ src.core.dataLoader
├── items.json ────→ src.core.dataLoader
├── encounters.json ──→ src.util.getEnc() ──→ src.systems.encounter_system
└── types.json ───────→ src.util.calculateMultiplier() ──→ src.entities.pokemonBattle
```

---

## 9. Known Issues & Technical Debt

### Bugs in Active Code
1. **Poison damage uses float division**: `self.maxHp // 12.5` returns a float due to the 12.5 being a float; should be `self.maxHp // 8` (12.5% of max = max/8)
2. **Critical hits ignore stat modifiers**: `damageFoePokemon` uses raw `pokemon.stats.defence` instead of `pokemon.getStat("defence")` on crit
3. **Dead code in type check**: `elif mult == 0:` on line 145 can never be reached since `mult` is never 0 (it's 0.0, which is falsy, caught by `elif mult < 1:`)
4. **Enemy hardcoded to Tackle**: `battleView.py:34` always assigns `PlayerPokemonMove("tackle", 35)` to wild Pokémon
5. **No move index validation**: `PokemonBattle.useMove()` doesn't validate that the move index is in range
6. **Evolution re-trigger**: `pokemonBattle.py:235` (`gainExp`) checks `evolution.levelCap == self.level` but doesn't check if already evolved
7. **`_pixelated` private attribute access**: 4 files access `manager._pixelated` which is a private attribute of `arcade.gui.UIManager`

### Architectural Issues
1. **Global singletons**: `gameContext.py` creates module-level instances that are implicitly imported everywhere
2. **No dependency injection**: Systems directly import `gameContext` globals
3. **Duplicate stat formulas**: HP calculation duplicated in `BagSystem`, `PokemonBattle`, `PokemonMenuUi`
4. **`util.py` opens files on every call**: `calculateMultiplier()` opens `types.json`, `getEnc()` opens `encounters.json` every invocation
5. **Tight coupling**: `BattleView` directly handles battle logic, UI, and state transitions
6. **CamelCase + snake_case mixed**: `pokemonBattle.py` vs `battle_ui_manager.py`, inconsistent across codebase
7. **Magic numbers throughout**: `-110`, `1.9`, `3.0`, `7`, `0.03`, `1.5`, `12.5`, `100`, `5`, `2` scattered in code
8. **No type checking in CI**: Only `ruff` formatting but no `pyright` or `mypy` enforcement
9. **No tests**: Zero test files for the game logic

### Code Smells
- `evolvingView.py` uses `manager.enable()` but `bagUi.py` does not
- `setup_invetory` typo in `bagUi.py:101`
- `debug_ui.py` references `manager.static_widgets_container` which doesn't exist in current `BattleUiManager`
- `len(messages) - 1 > 0` confusing pattern in `battleSystem.py:103`

---

## 10. Developer Tooling

| Tool | Usage | Configuration |
|------|-------|---------------|
| **uv** | Package manager, venv, dependency sync | `pyproject.toml` |
| **Arcade** 3.3.3+ | Game framework (windowing, sprites, UI, tilemaps, camera) | `pyproject.toml` |
| **Pydantic** 2.12.5+ | Configuration validation (`data/config.py`) | `pyproject.toml` |
| **Ruff** 0.15.7+ | Linting and formatting | `pyproject.toml`, CI in `.github/workflows/lint.yaml` |
| **Pyright** 1.1.409+ | Type checking (dev dependency, not CI-enforced) | `pyproject.toml` venv config |
| **Tiled** | Map editor for `.tmx` files | N/A (external tool) |

### Metadata
- **Python version**: 3.14+ (requires new-style type parameter syntax)
- **Dependencies**: `arcade>=3.3.3`, `pydantic>=2.12.5`
- **Dev dependencies**: `pyright>=1.1.409`, `ruff>=0.15.7`
- **CI**: GitHub Actions — runs `ruff format --check` and `ruff check` on push to main
- **Run**: `uv run main.py`
- **Python files**: 27 (22 in src/, 3 in root, 1 in data/, 1 in .github/)

---

## 11. Conclusion

Pokémon Emerald But BETTER is a technically ambitious recreation of a classic Game Boy Advance game using Python and the Arcade game framework. The project demonstrates:

- **Deep understanding of Pokémon Gen III mechanics**: The damage formula, stat calculation, type effectiveness matrix, status conditions, STAB, critical hit system, and evolution mechanics are all faithfully implemented.
- **Clean separation of concerns**: Despite some remaining tight coupling, the architecture clearly distinguishes between models (data), views (Arcade Views + UI components), controllers (input processing), and systems (movement, encounters, battle).
- **Professional tooling**: Uses modern Python tooling (uv, Ruff, Pydantic, GitHub Actions CI).
- **Active development**: The refactoring from monolithic classes to modular architecture indicates ongoing maintenance and improvement.

The largest technical gaps are the lack of audio, limited maps/content, missing trainer battles, no Pokémon catching mechanics, many known bugs, and the dual-maintenance burden from the partial refactoring. The codebase would benefit most from completing the architectural migration, adding tests, fixing the known bugs, and implementing the core missing gameplay features (trainers, Pokémon Centers, Poké Marts, and catching).
