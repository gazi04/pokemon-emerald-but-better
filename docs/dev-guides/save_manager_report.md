# Save Manager — How It's Written, How It Works, How It Connects

## 1. What it is, in one line

`SaveManager` owns the **single in-memory `PlayerSave` and the disk round-trip for it**: it loads the save at boot (with a fallback chain), holds the live player state for the whole session, and writes it back atomically on request. It does *file I/O and lifecycle only* — the JSON ↔ object shape is delegated to `PlayerSerializer`.

---

## 2. The cast of characters

Saving is not one class — it's a small collaboration. Know the five pieces:

| Piece | File | Responsibility |
|---|---|---|
| **`SaveManager`** | `src/core/save_manager.py` | Load on boot, hold `player`, write atomically. File I/O + fallback only. |
| **`PlayerSerializer`** | `src/core/player_serializer.py` | The save *schema* — `PlayerSave` ↔ `dict`. Single source of field truth. |
| **`PlayerSave`** | `src/model/save/player.py` | The actual persisted data (party, items, money, seen, npc_states). Pure dataclass. |
| **`PlayerMotion`** | `src/model/motion/player_motion.py` | Transient overworld position; its 4 fields become the `position` block. |
| **`PlayerManager`** | `src/core/player_manager.py` | Facade for *mutating* `PlayerSave` during play; also captures NPC states pre-save. |

Rule of thumb: **`SaveManager` = disk. `PlayerSerializer` = shape. `PlayerSave` = data. `PlayerManager` = mutation.** They never blur.

---

## 3. The save files on disk

Four paths, defined as constants at the top of `save_manager.py`:

| Constant | Path | Role |
|---|---|---|
| `SAVE_PATH` | `data/save.json` | The live save. Auto-created on first write. |
| `SAVE_TMP_PATH` | `data/save.tmp.json` | Scratch file written first, then renamed into place. |
| `SAVE_BAK_PATH` | `data/save.bak.json` | Previous good save, copied aside before each overwrite. |
| `DEFAULT_PATH` | `data/player.json` | Shipped new-game state. Read-only fallback; never written. |

---

## 4. How it's written — load (boot)

`SaveManager.__init__` calls `load()` immediately, so a manager is never in an un-loaded state.

```python
def load(self):
    candidates = [p for p in (SAVE_PATH, SAVE_BAK_PATH) if os.path.exists(p)]
    candidates.append(DEFAULT_PATH)

    last_error = None
    for path in candidates:
        try:
            with open(path) as f:
                data = json.load(f)
            self.player = PlayerSerializer.deserialize(data)
            self.saved_position = data.get("position")
            if path != SAVE_PATH:
                log.warning("Loaded save from fallback '%s'", path)
            return
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as e:
            last_error = e
            log.warning("Failed to load save '%s': %s", path, e)

    raise RuntimeError(f"Could not load any save (tried {candidates})") from last_error
```

The design point is the **fallback chain**: `save.json → save.bak.json → player.json`. A corrupt or partial save (crash mid-write, bad hand-edit, schema drift) must never brick startup — it falls through to the backup, then to the shipped default. Only an unrecoverable install (even `player.json` unreadable) raises. Note `saved_position` is read here too — it is *not* a field of `PlayerSave`, it lives at the top level of the JSON and is stashed separately.

---

## 5. How it's written — flush (save)

```python
def flush_save(self, player_state) -> bool:
    try:
        data = PlayerSerializer.serialize(self.player, player_state)

        with open(SAVE_TMP_PATH, "w") as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())  # force tmp to physical disk

        if os.path.exists(SAVE_PATH):
            shutil.copy2(SAVE_PATH, SAVE_BAK_PATH)  # keep a backup

        os.replace(SAVE_TMP_PATH, SAVE_PATH)  # atomic rename
        self.saved_position = data.get("position")
        return True
    except Exception:
        log.exception("Save failed")
        return False
```

This is the **atomic-write pattern**, and every step earns its place:

1. **Serialize** the live `player` + the passed `player_state` (a `PlayerMotion`) into one dict.
2. **Write to `.tmp`**, then `flush()` + `os.fsync()` — guarantees the bytes are on physical disk, not just in the OS buffer, before the rename.
3. **Copy the current `save.json` to `.bak`** — so the previous good save survives.
4. **`os.replace(tmp → save.json)`** — an atomic rename on the same filesystem. A reader sees either the whole old file or the whole new file, never a half-written one.
5. **Returns `bool`** — `True` on success, `False` (logged, not raised) on any failure. The caller reports this outward; a failed save never crashes the game.

---

## 6. How the shape is defined — `PlayerSerializer`

`SaveManager` knows *nothing* about fields. The schema lives entirely in `PlayerSerializer`, three static methods:

- **`serialize(player, motion=None) -> dict`** — every persisted field: `pokemons`, `items`,   `pokeballs`, `seen`, `money`, `npc_states`, and (if `motion` is given) a `position` block.
- **`deserialize(data) -> PlayerSave`** — the inverse, with `.get(...)` defaults for the   optional/newer fields (`seen`, `money`, `npc_states`) so old saves still load.
- **`position(motion) -> dict`** — the *one* definition of the position schema (`map_name`/`direction`/`pixel_x`/`pixel_y`). Both `serialize` and `flush_save`'s callers route through it, so the position shape can't drift between write sites.

Why `position` is separate from `PlayerSave`: it is transient overworld *render* state (`PlayerMotion`), not party data. It rides at the top level of the JSON alongside the serialized profile, not inside it.

---

## 7. How it connects — the save trigger flow

Nothing calls `flush_save` directly except the Director. The trigger is an event chain (see `event_system_report.md`):

```
 MenuView "Save" selected
   └─ publish(SaveGameRequestEvent)
        └─ GameDirector._on_save_request   (subscribed)
             ├─ player_manager.capture_npc_states()   # snapshot NPC flags into PlayerSave
             ├─ success = save_manager.flush_save(overworld.player_state)
             └─ publish(SaveCompletedEvent(success))
                  └─ MenuView._on_save_completed   (shows "Saved!" / failure)
```

Key wiring facts:

- **The Director owns the one `SaveManager`** (`game_director.py:36`). It is constructed once and injected into `PlayerManager`. There is exactly one `PlayerSave` for the session.
- **`capture_npc_states()` runs first.** NPC interaction flags live in `NPCManager` during play; this call flushes them into `PlayerSave.npc_states` so they're in the dict the serializer writes.
- **`overworld.player_state`** (a `PlayerMotion`) is passed as the `position` source — that's how the player's map + tile location get into the save.
- **The result comes back as an event**, not a return value — the menu reacts to  `SaveCompletedEvent`, staying decoupled from the Director.

---

## 8. How it connects — the load-back flow

On the read side, `saved_position` is consumed by `OverworldView` at construction (`overworld_view.py:62`):

```python
saved = self.save_manager.saved_position
if saved:
    self.player_state.map_name = saved.get("map_name", self.player_state.map_name)
    self.player_state.direction = saved.get("direction", self.player_state.direction)
    self.setup(f"assets/map/{self.player_state.map_name}.tmx")
    self.player_state.pixel_x = saved["pixel_x"]
    self.player_state.pixel_y = saved["pixel_y"]
else:
    self.setup()  # fresh game — default spawn
```

So `position` round-trips: `PlayerMotion → serialize → save.json → saved_position →PlayerMotion`. The party/items/money side round-trips through `SaveManager.player` (the`PlayerSave`), which `PlayerManager` reads and mutates all session long.

---

## 9. How party progress reaches the save — the mutation path

During play, nothing writes `PlayerSave` fields directly; mutations go through `PlayerManager`, which is the same object the whole game shares. Two examples:

- **After a battle**, `BattleSystem.save()` calls `player_manager.persist_active_pokemon(your_pokemon, has_evolved)` — pushing the battle Pokémon's hp/pp/level (and evolution) back into `PlayerSave`. Persistence lives in `PlayerManager`, not in `BattleSystem`.
- **Picking up money/items** goes through `add_money` / `add_item`, again mutating the shared `PlayerSave`.

These mutations are **in-memory only**. They become durable only when the player saves and `flush_save` writes the dict. (One exception worth noting: whiting out heals the team via `heal_team`, and the post-battle `save()` persists that — but a *true* on-disk write still needs a flush.)

---

## 10. How to use it

### To save from new code
Don't call `flush_save` directly. Publish the request event and let the Director handle it:

```python
from src.core.event_bus import global_bus
from src.core.events import SaveGameRequestEvent

global_bus.publish(SaveGameRequestEvent())
# react to SaveCompletedEvent(success) if you need to confirm
```

### To mutate what gets saved
Go through `PlayerManager` — never poke `save_manager.player` fields from a view/system:

```python
self.player_manager.add_money(500)
self.player_manager.add_item("potion", 2)
self.player_manager.persist_active_pokemon(battle_pokemon, has_evolved=False)
```

### To add a new persisted field
This is a **two-file change, and only two files**:

1. Add the field to `PlayerSave` (`src/model/save/player.py`) with a default.
2. Add it to **both** `PlayerSerializer.serialize` and `.deserialize` — use `data.get("field", default)` in `deserialize` so old saves without the field still load.

Do *not* touch `SaveManager` — it shapes nothing. If you forget the serializer, the field silently won't persist (this was the exact bug the §7 refactor fixed for `money`/`npc_states`).

### To read the save at boot
It's already loaded — `save_manager.player` is populated by `__init__`. Read position via `save_manager.saved_position` (a dict or `None`).

---

## 11. Lifecycle & guarantees

- **Loaded eagerly.** `__init__` → `load()`; the manager is never half-initialized.
- **One instance, one `PlayerSave`.** The Director builds it; everything else gets it injected. No parallel save state (the old `game_context.py` duplicate was deleted — plan §1).
- **Atomic on disk.** fsync + backup-copy + `os.replace` mean a crash mid-save leaves either the old file intact or the backup recoverable — never a corrupt `save.json`.
- **Fault-tolerant on load.** Three-tier fallback; only a broken *install* (no readable file at all) raises.
- **Failure is a return value, not a crash.** `flush_save` returns `False` and logs; the game keeps running and the UI reports it via `SaveCompletedEvent`.

---

## 12. Honest limitations

- **No save versioning.** `save.json` has no `version` field, so a future schema change can't run a migration — it relies on `deserialize`'s `.get(...)` defaults to tolerate missing keys. Adding a `version` + migration step is a tracked follow-up (`readability_refactor_plan.md`, "Further ideas").
- **Single save slot.** One `SAVE_PATH`; no multi-slot or named saves.
- **`position` lives outside `PlayerSave`.** It round-trips correctly but as a top-level JSON key, so the save isn't one self-contained object. A `SaveGame {profile, position}` wrapper was considered and deferred.
- **In-memory until flush.** All mutations are lost on a crash before the next save — there is no autosave or journaling.
