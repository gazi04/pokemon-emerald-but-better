# DataLoader — Report & Guide

## 1. What it is

`DataLoader` is the project's **read-only static-data store**. At startup it reads six JSON files from `data/` and caches them in memory — four parsed into typed model objects, two (`encounters`, `types`) kept as raw dicts. For the rest of the session, anything that needs to know "what is a treecko / what does tackle do / how much is a potion / what does this NPC say / what spawns in this grass / how effective is fire on grass" asks the `DataLoader` — never the disk.

It owns **species/template data only** (the `model/static/` layer). It does **not** hold save state (that's `SaveManager`/`PlayerSave`) and it never mutates — every getter returns the same shared, read-only object.

Two classes split the job (clean SRP):
- **`DataLoader`** — file I/O + caching + lookup getters.
- **`GameDataParser`** — pure `dict → model` mapping. No file access.

---

## 2. What it loads

| Source file            | Parsed by          | Cached as         | Model type                        |
| ---------------------- | ------------------ | ----------------- | --------------------------------- |
| `data/pokemon.json`    | `parse_pokemons`   | `self.pokemons`   | `dict[str, PokemonSpecies]`       |
| `data/moves.json`      | `parse_moves`      | `self.moves`      | `dict[str, PokemonMove]`          |
| `data/items.json`      | `parse_items`      | `self.items`      | `dict[str, ItemSpecies]`          |
| `data/npc_dialog.json` | `parse_npc_dialog` | `self.npc_dialog` | `dict[str, NpcSpecies]`           |
| `data/encounters.json` | — (raw)            | `self.encounters` | `dict` (per-map grass tables)     |
| `data/types.json`      | — (raw)            | `self.types`      | `dict` (type-effectiveness chart) |

The first four caches are keyed by the **lowercase name** that is the JSON top-level key (`"treecko"`, `"tackle"`, `"potion"`). `encounters`/`types` are kept as the **raw parsed dict** (no model layer) — they're consumed by `EncounterSystem` (per grass step) and `combat_calculator` (per damage calc), so caching them here removes the per-call file read that `src/util.py` used to pay.

---

## 3. How it's written

### `DataLoader` (`data_loader.py`)
```python
class DataLoader:
    def __init__(self):
        self.pokemons   = GameDataParser.parse_pokemons(self._read("data/pokemon.json"))
        self.moves      = GameDataParser.parse_moves(self._read("data/moves.json"))
        self.items      = GameDataParser.parse_items(self._read("data/items.json"))
        self.npc_dialog = GameDataParser.parse_npc_dialog(self._read("data/npc_dialog.json"))
        self.encounters = self._read("data/encounters.json")   # raw dict, per-map
        self.types      = self._read("data/types.json")        # raw type chart

    def _read(self, path: str) -> dict:
        with open(path) as f:
            return json.load(f)

    def get_pokemon(self, name): return self.pokemons.get(name)   # -> PokemonSpecies | None
    def get_move(self, name):    return self.moves.get(name)      # -> PokemonMove | None
    def get_item(self, name):    return self.items.get(name)      # -> ItemSpecies | None
```
- **Eager, all-at-once load.** Everything is parsed in `__init__`. If a file is missing or malformed, construction throws immediately (fail-fast at boot, not mid-battle).
- **`.get()` getters return `None`** on a miss — callers must null-check (most do; e.g. `battle_view._refresh_active_pokemon_ui` guards `get_move(...)`).
- Note `npc_dialog` has **no getter** — consumers read the dict directly (`data_loader.npc_dialog.get(npc_id)` / `data_loader.npc_dialog[npc_id]`).

### `GameDataParser` (`game_data_parser.py`)
A bag of `@staticmethod`s, one per file, each a pure `dict → model`:
- **`parse_pokemons`** — builds `SpritePaths(**raw["sprites"])`, `PokemonStat(**raw["stats"])`, an optional `PokemonEvolution`, and an optional `learnset` (`[LearnsetMove(move, level)]` from `raw.get("learnset", [])`), into a `PokemonSpecies`. Tolerant: `raw.get("baseExp", 0)`, `raw.get("catchRate", 45)`, etc.
- **`parse_moves`** — converts each effect's stringly-typed fields into **enums at load time**: `EffectType(e["type"])`, `Stat(...)`, `StatusEffect(...)`. After this point the rest of the code works with typed enums, not strings.
- **`parse_items`** — `ItemEffect(type, amount, catch_rate)` list → `ItemSpecies`; `type` is now parsed to `EffectType(e["type"])` at load (mirrors `parse_moves`), so `ItemEffect.type` is a typed enum, not a string.
- **`parse_npc_dialog`** — `{state: [lines]}` map into `NpcSpecies`; tolerates the legacy flat-list form by mapping it to `"default"`. Also builds a `Trainer` party from `raw["team"]`.

Putting all `dict → object` extraction in one place is deliberate: the models stay **pure dataclasses** (fields only), parsing lives in exactly one file.

---

## 4. The models it produces (`src/model/static/`)

Read-only species data — no arcade, no save state:
- **`PokemonSpecies`** (`pokemon.py`) — `baseExp`, `catch_rate`, `abilities`, `types`, optional `evolution`, `sprites: SpritePaths`, `stats: PokemonStat`, and `learnset: list[LearnsetMove]` (defaults to `[]`). `PokemonStat` carries the **canonical stat math** (`scaled`, `max_hp`, `at_level`) reused across the codebase. The `learnset` (move + level-learned) feeds `wild_moveset.select_wild_moves` to give wild foes real movesets.
- **`PokemonMove`** (`pokemon.py`) — `category`/`type`/`power`/`accuracy`/`pp` + a list of typed `PokemonMoveEffect`.
- **`ItemSpecies`** (`item.py`) — `description`, `price`, `effects: list[ItemEffect]`.
- **`NpcSpecies`** (`npc.py`) — `dialogs: {state: [lines]}`, `action_after_dialog`, and a `Trainer` (`trainer.py`) party of `TrainerPokemon`. `get_dialog(state)` falls back gracefully (requested → default → first_encounter → any → `["..."]`).

---

## 5. How it connects

```
        main.py ──► GameDirector.__init__
                        │ self.data_loader = DataLoader()       (built once)
                        │
   injected into ───────┼─────────────► PlayerManager(save_manager, data_loader)
   every view/system    │
   that needs species   ├─ BattleView / BattleSystem  (get_pokemon, get_move)
   data:                ├─ BagSystem / ShopView        (get_item)
                        ├─ EncounterSystem             (get_pokemon for wild foes)
                        ├─ Overworld / DialogView      (npc_dialog[...])
                        └─ Pokedex / PokemonInfo UIs   (full species lookups)

        DataLoader ──delegates dict→model──► GameDataParser ──reads──► data/*.json
```

- **Single instance, dependency-injected.** `GameDirector` builds one `DataLoader` in `__init__`   and passes that same object to every view/system it constructs (see `game_director_report.md`). No global, no second copy — mirrors the "one `SaveManager`" rule.
- **~17 consumers** across `states/`, `systems/`, `ui/`, and `PlayerManager` (e.g. `player_manager.heal_team` reads `get_pokemon(...).stats`,  `battle_system.attempt_catch` reads `get_pokemon(...).catch_rate`).
- **Boundary:** `DataLoader` (core) depends downward on `model/static` + `enums`. Models never import arcade or the loader → the static-data layer stays pure and testable.

---

## 6. Data file shapes (to add content)

Add a Pokémon/move/item/NPC = **add a JSON entry, no code** (the scalable part). Example shapes:

```jsonc
// pokemon.json
"treecko": {
  "baseExp": 62, "evolution": null, "catchRate": 45,
  "abilities": ["overgrow"], "types": ["grass"],
  "sprites": { "back": "...png", "front": "...png" },
  "stats": { "hp": 40, "attack": 65, "defence": 35,
             "special_attack": 45, "special_defence": 55, "speed": 70 },
  "learnset": [ { "move": "tackle", "level": 1 },
                { "move": "spore",  "level": 9 } ]
}
// moves.json
"tackle": { "category": "physical", "type": "normal", "power": 40,
            "accuracy": 100, "pp": 35, "effects": [] }
// items.json
"potion": { "description": "...", "price": 300,
            "effects": [{ "type": "heal", "amount": 20 }] }
// encounters.json — per map
"route_101": { "encounter_rate": 0.18,
               "grass": [ { "name": "poochyena", "levels": [3,5], "weight": 1 } ] }
```

Keys to mind: `baseExp`/`catchRate` are **camelCase in JSON** (external on-disk contract — the parser maps them to snake_case fields). `evolution` is `null` or `{ "to": "...", "level": N }`. `learnset` is optional (absent → `[]` → wild falls back to Tackle). A move/item `effects` entry must use a string the enums accept (`EffectType`/`Stat`/`StatusEffect`) or the parser raises at load. `encounters.json` per map takes an optional `encounter_rate` (falls back to `constants.ENCOUNTER_RATE`) beside its `grass` table.

---

## 7. How to use it

### Get the instance
Never construct your own — accept the injected one:
```python
class MyView(GameView):
    def __init__(self, ..., data_loader: DataLoader):
        self.data_loader = data_loader
```
(If you add a new view, `GameDirector._build_*` already passes `self.data_loader` — see that report.)

### Look something up
```python
species = self.data_loader.get_pokemon(name)     # PokemonSpecies | None
if species is None:                              # always null-check
    ...
move = self.data_loader.get_move("tackle")
item = self.data_loader.get_item("potion")
npc  = self.data_loader.npc_dialog.get(npc_id)   # dict access, no getter
```

### Reuse the stat math (don't re-derive it)
```python
from src.model.static.pokemon import PokemonStat
max_hp = PokemonStat.max_hp(species.stats.hp, level)
```

---

## 8. Gotchas & rough edges

- **`types.json` / `encounters.json` are now cached here** (`self.types` / `self.encounters`, added 2026-06-25). `src/util.py` no longer reads them — `get_enc`/`calculate_multiplier` were removed. `EncounterSystem` reads `data_loader.encounters[map]`; `combat_calculator.calculate_damage` takes the chart as a `type_chart` param (passed `data_loader.types` by `BattleSystem`), staying pure. No more per-step/per-calc file I/O.
- **Getters can return `None`.** A typo'd name or missing entry yields `None`, not an error — null-check.
- **Eager boot load.** A malformed `data/*.json` crashes at startup with a `KeyError`/`JSONDecodeError` deep in the parser. The plan suggests pydantic/jsonschema validation on load for a clearer message; not yet done (`data/config.py` already uses pydantic as the model to copy).
- **Lookup keys are lowercase names.** Callers often `name.lower()` before lookups (`get_pokemon(enemy.name.lower())`) — keep that convention.
- **`DataLoader` path list is hand-wired** in `__init__`. If data categories keep multiplying, a `{name: path}` table would help — minor, deferred (YAGNI).

---

## 9. One-paragraph summary

`DataLoader` reads six static JSON files once at boot: four (`pokemon`, `moves`, `items`, `npc_dialog`) parsed into typed model dicts via the pure `GameDataParser` (which also converts stringly-typed effect fields into enums), plus `encounters` and `types` kept as raw dicts. `GameDirector` builds one instance and injects it into every view/system that needs static data; getters return shared read-only objects (or `None`). Add content by adding a JSON entry — no code. The former wart (per-call re-parsing of `types`/`encounters` in `src/util.py`) is fixed — both are cached here now.
