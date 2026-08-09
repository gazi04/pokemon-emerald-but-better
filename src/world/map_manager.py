"""Single authority for the active overworld map.

Exactly one map is resident at a time. The MapManager loads/unloads maps,
tracks the current id, resolves spawn points, and executes transitions. Every
relocation — a doorway transition, a Fly, a Teleport, a warp tile, a scripted
story warp — funnels through `warp()`, so there is exactly one place to hook
map scripts, dynamic NPC spawning and persistence (`on_load` / `on_unload`).

It knows nothing about rendering or input; OverworldView wires the returned
LoadedMap into the scene. That keeps the map system decoupled and testable.
"""

from collections.abc import Callable

from src.core.logger import get_logger
from src.states.map_loader import MapLoader, LoadedMap
from src.world.map_registry import MapRegistry
from src.world.transition import Transition

log = get_logger(__name__)

# A spawn target: a named spawn point, an explicit (x, y) world position, or
# None (use the map's "default" spawn).
Spawn = str | tuple[float, float] | None

MapHook = Callable[[str, LoadedMap], None]

# Spawn objects mark the tile the player lands on, but the player sprite is
# anchored slightly lower than a tile's center — this nudge lines the sprite up
# with the tile so arrivals don't look half-sunk into the floor.
SPAWN_Y_OFFSET = 8


class MapManager:
    def __init__(
        self,
        loader: MapLoader,
        registry: MapRegistry,
        player_state,
        on_load: MapHook | None = None,
        on_unload: MapHook | None = None,
    ):
        self._loader = loader
        self._registry = registry
        self._player_state = player_state
        self._on_load = on_load
        self._on_unload = on_unload

        self.current_map_id: str | None = None
        self.loaded: LoadedMap | None = None

    # ------------------------------------------------------------------
    # Core lifecycle
    # ------------------------------------------------------------------

    def load(self, map_ref: str, spawn: Spawn = None) -> LoadedMap:
        """Unload the current map, load `map_ref` (id/alias/path), place the
        player at `spawn`, and return the LoadedMap for the view to wire in."""
        map_id = self._registry.resolve(map_ref)

        self._unload()

        loaded = self._loader.load(self._registry.path_for(map_id), map_id)
        self.loaded = loaded
        self.current_map_id = map_id
        self._player_state.map_name = map_id

        self._place_player(loaded, spawn)

        log.info("Active map -> '%s' (spawn=%r)", map_id, spawn)
        if self._on_load:
            self._on_load(map_id, loaded)
        return loaded

    def warp(self, map_ref: str, spawn: Spawn = None) -> LoadedMap:
        """Public relocation seam reused by Fly, Teleport, warp tiles and
        scripted story warps. Same machinery as a normal transition."""
        return self.load(map_ref, spawn)

    def transition(self, transition: Transition) -> LoadedMap:
        """Execute a parsed transition (named spawn preferred, coords legacy)."""
        return self.load(transition.target_map, transition.spawn)

    def has_spawn(self, name: str) -> bool:
        return bool(self.loaded and name in self.loaded.spawns)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _place_player(self, loaded: LoadedMap, spawn: Spawn) -> None:
        position = self._resolve_spawn(loaded, spawn)
        if position is not None:
            self._player_state.pixel_x, self._player_state.pixel_y = position
            self._player_state.pixel_y += SPAWN_Y_OFFSET

    def _resolve_spawn(
        self, loaded: LoadedMap, spawn: Spawn
    ) -> tuple[float, float] | None:
        if spawn is None:
            return loaded.spawns.get("default")
        if isinstance(spawn, str):
            position = loaded.spawns.get(spawn)
            if position is None:
                log.warning(
                    "Spawn '%s' not found on '%s'; falling back to 'default'",
                    spawn,
                    self.current_map_id,
                )
                return loaded.spawns.get("default")
            return position
        return spawn  # explicit (x, y)

    def _unload(self) -> None:
        """Drop the active map's assets and fire the persistence/script seam."""
        if self.loaded is None or self.current_map_id is None:
            return
        if self._on_unload:
            self._on_unload(self.current_map_id, self.loaded)
        try:
            self.loaded.npcs.clear()
        except Exception:
            log.exception(
                "Error clearing NPCs while unloading '%s'", self.current_map_id
            )
        self.loaded = None
