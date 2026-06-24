from dataclasses import dataclass

import arcade

from src.constants import TILE_SIZE
from src.core.logger import get_logger
from src.systems.npc_controller import NpcController
from src.systems.npc_behaviors import make_behavior
from src.entities.npc import Npc

log = get_logger(__name__)


@dataclass
class LoadedMap:
    """Everything a freshly-loaded map produces. OverworldView wires these in."""

    tile_map: arcade.TileMap
    scene: arcade.Scene
    npcs: arcade.SpriteList
    npc_controller: NpcController
    bush_tiles: set[tuple[int, int]]


class MapLoader:
    """Builds a map's runtime objects (tilemap, scene, NPCs, NPC controller,
    bush set) from a .tmx path. No view or render state — pure map build, so
    OverworldView keeps only draw + input + lifecycle + nav."""

    def __init__(self, movement_system, player_state):
        self.movement_system = movement_system
        self.player_state = player_state

    def load(self, map_path: str) -> LoadedMap:
        layer_options = {
            "collision": {"use_spatial_hash": True},
            "bush": {"use_spatial_hash": True},
            "transitions": {"use_spatial_hash": True},
        }
        tile_map = arcade.tilemap.load_tilemap(
            map_path, scaling=2.0, layer_options=layer_options
        )
        scene = arcade.Scene.from_tilemap(tile_map)

        npcs = self._spawn_npcs(tile_map, scene)
        npc_controller = self._build_npc_controller(tile_map, scene, npcs)
        bush_tiles = self._extract_bush_tiles(scene)

        return LoadedMap(tile_map, scene, npcs, npc_controller, bush_tiles)

    def _spawn_npcs(
        self, tile_map: arcade.TileMap, scene: arcade.Scene
    ) -> arcade.SpriteList:
        npcs = arcade.SpriteList(use_spatial_hash=False)
        npc_layer = tile_map.get_tilemap_layer("npc")
        if npc_layer:
            scene.remove_sprite_list_by_name("npc")
            for obj in npc_layer.tiled_objects:
                props = obj.properties or {}
                npc = Npc(
                    x=obj.coordinates.x * 2 + obj.size.width,
                    y=(tile_map.height * tile_map.tile_height - obj.coordinates.y) * 2
                    + obj.size.height / 2,
                    npc_id=props.get("npc_id", ""),
                    behavior=make_behavior(props),
                    facing=props.get("facing", "down"),
                )
                npcs.append(npc)
        return npcs

    def _build_npc_controller(
        self, tile_map: arcade.TileMap, scene: arcade.Scene, npcs: arcade.SpriteList
    ) -> NpcController:
        try:
            collision_tiles = scene["collision"]
        except KeyError:
            log.debug("No 'collision' layer on map; using empty collision set")
            collision_tiles = arcade.SpriteList()

        map_width = tile_map.width * tile_map.tile_width * 2
        map_height = tile_map.height * tile_map.tile_height * 2

        return NpcController(
            npcs=npcs,
            movement_system=self.movement_system,
            collision_tiles=collision_tiles,
            player_state=self.player_state,
            map_width=map_width,
            map_height=map_height,
        )

    @staticmethod
    def _extract_bush_tiles(scene: arcade.Scene) -> set[tuple[int, int]]:
        """
        Build a set of integer (grid_x, grid_y) tuples from the bush
        SpriteList. Done once at map load — O(1) lookup at runtime.
        The bush layer sprites are scaled 2x, but their center_x/center_y
        are in pixel space. Dividing by TILE_SIZE gives grid coords that
        match MovementSystem's grid_x = round(pixel_x / TILE_SIZE).
        """
        try:
            tiles: set[tuple[int, int]] = set()
            bush_layer = scene["bush"]
            for sprite in bush_layer:
                gx = round(sprite.center_x / TILE_SIZE)
                gy = round(sprite.center_y / TILE_SIZE)
                tiles.add((gx, gy))
            return tiles
        except Exception:
            log.exception("Failed to extract bush tiles; treating map as bushless")
            return set()
