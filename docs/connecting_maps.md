# Connecting Maps

How to link two maps so the player can walk between them. Authoring is **100%
in Tiled** — no code changes per connection.

---

## The model in one minute

- **Map id** = the map's path under `assets/map/`, without `.tmx`.
  `assets/map/oldale_town/pokemon_center.tmx` → id `oldale_town/pokemon_center`.
- A **transition** (a door) says *where to go* and *where to land*.
- A **spawn point** is a *named landing spot* on a map.
- A connection is **two** transitions (one each way), each pointing at a spawn
  on the other map.

```
   MAP A                         MAP B
 ┌───────────┐   target_map:B  ┌───────────┐
 │  [door]───┼──── target_spawn:from_A ───►│ [spawn "from_A"]
 │ [spawn    │◄─── target_spawn:from_B ────┼───[door]  │
 │  "from_B"]│   target_map:A              │           │
 └───────────┘                             └───────────┘
```

`MapManager` loads only the target map, then drops the player on the named spawn.

---

## Two object layers you author

| Layer name    | Object type              | Purpose                                   |
|---------------|--------------------------|-------------------------------------------|
| `transitions` | **Rectangle** (preferred)| The region you walk into. Draw it over the door tile(s). Detected by point-in-rect. |
| `spawns`      | **Rectangle**            | A named landing spot. 16×16, name it. |

Both are **plain rectangle objects** — just draw them. Each transition rectangle
is independent and carries its own properties, so a map can have as many doors
as you want (a plain *tile* layer can't — it shares one property set per tile).

> **Legacy note:** older maps used *tile/gid* objects for doors. Those still
> work (via a sprite hit-test fallback), so nothing needs migrating — but new
> transitions should be plain rectangles.

### Transition object properties

| Property        | Example                     | Notes |
|-----------------|-----------------------------|-------|
| `target_map`    | `oldale_town/pokemon_center`| destination **map id** (include the subfolder) |
| `target_spawn`  | `entrance`                  | a spawn **name** on the destination map |

Legacy `destination map` + `x` + `y` (world pixels) still works, so old doors
keep functioning — but new ones should use `target_map` + `target_spawn`.

### Spawn object

- Draw a **16×16 rectangle** on the `spawns` layer.
- Set its **Name** to something unique on that map (e.g. `entrance`,
  `pokecenter_door`, `south_gate`). (A `name` *property* also works.)
- Place it on the tile the player should stand on — usually **one tile inside**
  the doorway, so they don't immediately re-trigger the door.
- A spawn named **`default`** is used for new-game start and as a fallback when a
  requested spawn is missing.

---

## Step-by-step in Tiled

To connect **Map A** ⇄ **Map B**:

1. **Map B** — add (or open) the `spawns` layer. Draw a 16×16 rectangle where the
   player should appear when coming *from A*. Name it, e.g. `from_a`.
2. **Map A** — add (or open) the `spawns` layer. Draw a rectangle where the
   player appears coming *from B*. Name it, e.g. `from_b`.
3. **Map A** — on the `transitions` layer, draw a **rectangle** over the door
   tile(s). Add properties `target_map = <B's id>`, `target_spawn = from_a`.
4. **Map B** — draw a rectangle over its door with
   `target_map = <A's id>`, `target_spawn = from_b`.
5. Save both maps. Walk through — no code needed.

---

## Worked example (already in the repo)

`littleroot_town` ⇄ `oldale_town/pokemon_center`:

**`oldale_town/pokemon_center.tmx`**
```xml
<objectgroup name="transitions">
  <object gid="36802" x="239.9" y="233.1" width="16" height="16">
    <properties>
      <property name="target_map" value="littleroot_town"/>
      <property name="target_spawn" value="pokecenter_door"/>
    </properties>
  </object>
</objectgroup>

<objectgroup name="spawns">
  <object name="entrance" x="240" y="219" width="16" height="16"/>
</objectgroup>
```

**`littleroot_town.tmx`**
```xml
<objectgroup name="transitions">
  <object gid="706" x="1552" y="960" width="16" height="16">
    <properties>
      <property name="target_map" value="oldale_town/pokemon_center"/>
      <property name="target_spawn" value="entrance"/>
    </properties>
  </object>
</objectgroup>

<objectgroup name="spawns">
  <object name="pokecenter_door" x="1551.5" y="972" width="16" height="16"/>
</objectgroup>
```

---

## Preserved per-map content

Nothing else changes. These layers keep working exactly as before on every map:
`collision`, `bush` (wild-encounter zones), `npc`, `walkable`, `position`
(legacy new-game start).

---

## Reusing connections for other features

Everything relocation-related funnels through one method:

```python
map_manager.warp(map_id, spawn)  # spawn = a name, an (x, y), or None
```

So future features are just callers of `warp()`:

| Feature            | How to add it |
|--------------------|---------------|
| **Fly**            | Register an alias (`registry.register_alias("fly:oldale", "oldale_town")`) → `warp("fly:oldale", "fly_point")`. |
| **Teleport / Dig** | `warp(last_town_id, "entrance")`. |
| **Warp tile**      | Author it as a transition object on a floor tile instead of a door. |
| **Story warp**     | On an event, call `warp(target_map, spawn)`. |
| **Whiteout respawn** | Already wired: `warp("oldale_town/pokemon_center", "entrance")`. |
| **Map scripts / dynamic NPCs** | Hook `MapManager(on_load=..., on_unload=...)` — fires with `(map_id, LoadedMap)` on every load. |

---

## Coordinate math (only if a spawn lands wrong)

Spawn objects convert to world coordinates in one place —
`object_to_world()` in `src/states/map_loader.py`:

```
world_x = obj.x * 2 + obj.width
world_y = (map_height_in_tiles * 16 - obj.y) * 2 + obj.height / 2
```

This is the **same** transform used to place NPCs, so if NPCs sit right, spawns
will too. If a landing looks off by a tile, nudge the spawn rectangle in Tiled —
don't change the formula unless *every* map is off (then it's a one-line fix here
that fixes NPCs and spawns together).

---

## Checklist

- [ ] Door is a **rectangle** on the `transitions` layer, drawn over the door tile(s).
- [ ] Door has `target_map` (correct id, incl. subfolder) + `target_spawn`.
- [ ] Destination has a `spawns` rectangle with the **matching name**.
- [ ] Spawn sits **one tile inside** the door (no instant re-trigger).
- [ ] Both directions authored (A→B and B→A).
- [ ] Optional: a `default` spawn for fallback / new-game.
