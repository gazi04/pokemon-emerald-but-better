# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the game
uv run main.py

# Type check
uv run pyright

# Lint / format
uv run ruff check .
uv run ruff format .

# Tests (pytest, configured in pyproject.toml; testpaths=tests)
uv run pytest                                   # full suite
uv run pytest tests/unit/test_combat_calculator.py   # single file
```

Test suite lives in `tests/` (`unit/` + `integration/`, shared fixtures in
`tests/conftest.py`). Run `uv run pytest` to verify logic changes; run the game
directly (`uv run main.py`) to verify rendering/input.

**Flaky-test caution:** systems that call `random` (e.g. `combat_calculator`'s
`_roll_critical`, `_check_accuracy`) must be patched in tests that compare
damage/outcomes — e.g. `patch("src.core.combat_calculator._roll_critical", return_value=False)`.
Unpatched crit rolls cause intermittent failures like `assert 6 < 6`.

## Architecture

### Entry point flow

`main.py` → creates `arcade.Window` → hands it to `GameDirector` → `director.start()` shows the Overworld.

### Core layer (`src/core/`)

| File | Role |
|---|---|
| `game_director.py` | Single traffic cop for all view transitions. Owns `SaveManager`, `DataLoader`, and a `_view_cache`. Subscribes to navigation events and builds/shows views. |
| `event_bus.py` | Tiny pub/sub (`global_bus` singleton). All cross-layer communication goes through it. |
| `events.py` | All event dataclasses in one place. Three groups: Overworld, Battle, Navigation (`SwapViewEvent`, `CloseViewEvent`, `OverlayViewEvent`), Save/Load. |
| `save_manager.py` | Owns in-memory `PlayerProfile`. Reads `data/save.json` (falls back to `data/player.json`). `flush_save()` writes atomically via a `.tmp` then `os.replace`. |
| `data_loader.py` | Parses `data/pokemon.json`, `data/moves.json`, `data/items.json` into typed model objects at startup. |
| `game_context.py` | Legacy singleton `saveManager`/`dataLoader` — being phased out; prefer injected instances. |
| `combat_calculator.py` | Pure damage calc (`calculate_damage`). No mutation, no arcade. Uses `random` for crit/accuracy — patch in tests. Returns `CombatResult`. |
| `catch_calculator.py` | Pure capture-rate calc. |

### View layer (`src/states/`) — all are `arcade.View` subclasses

- **OverworldView** — persistent singleton (cached in `GameDirector._view_cache`). Owns `PlayerState`, `MovementSystem`, `EncounterSystem`, `PlayerSprite`.
- **BattleView** — transient, instantiated fresh each encounter with a `BattleSystem`.
- **EvolvingView** — transient post-battle evolution sequence.
- **MenuView / BagView / PokemonMenuView** — overlays stacked on top of Overworld without destroying its state.

### Navigation contract

Views never call `window.show_view()` directly. They publish events:
- `SwapViewEvent(target, payload)` — full takeover (battle, evolving)
- `OverlayViewEvent(target, payload)` — stack on top (menu, bag, pokemon_menu)
- `CloseViewEvent()` — return to Overworld

### Systems (`src/systems/`) — stateless logic, no arcade dependency

`MovementSystem`, `EncounterSystem`, `BattleSystem`, `BagSystem`, `PokemonMenuSystem`. They publish events and mutate `SaveManager` state; views subscribe to those events to update UI.

### Model layer (`src/model/`)

Pure dataclasses (`@dataclass`, some `pydantic.BaseModel` in `data/config.py`). No arcade imports.
- `PlayerProfile` / `PlayerPokemon` / `PlayerState` — live save state.
- `PokemonProfile` / `PokemonMove` / `PokemonStat` — read-only species data from `DataLoader`.

### UI components (`src/ui/`)

Layout parsed from Tiled `.tmx` files via `layout_parser.py`. UI managers (`BattleUiManager`, `BagUi`, etc.) render from model state; they do not own logic.

### Data files (`data/`)

- `config.json` — window/controls/game settings, loaded via pydantic `Config` model.
- `player.json` — default new-game player state.
- `save.json` — active save (auto-created on first save).
- `pokemon.json`, `moves.json`, `items.json`, `encounters.json`, `types.json` — static game data.

### Map assets (`assets/map/`, `assets/ui/`)

Tiled `.tmx` maps + `.tsx` tilesets. Maps are loaded by `OverworldView.setup()`. UI layouts (battle, bag, menu, etc.) are separate `.tmx` files parsed at view init.
