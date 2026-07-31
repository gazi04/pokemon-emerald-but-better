"""Tests for MapLoader's pure helpers: spawn extraction, collision-layer
fallback, and bush-tile grid building. `load()`/`_spawn_npcs()` construct real
arcade.Sprite/Npc/TileMap objects (texture loading, GL context) and are
exercised by running the game, not unit-tested here — same convention as the
rest of the entities/ layer."""

from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, Mock

import arcade
from pytiled_parser import ObjectLayer

from src.states.map_loader import MapLoader


def make_tile_map(layer=None, width=20, height=10, tile_width=16, tile_height=16):
    tile_map = MagicMock()
    tile_map.get_tilemap_layer.return_value = layer
    tile_map.width = width
    tile_map.height = height
    tile_map.tile_width = tile_width
    tile_map.tile_height = tile_height
    return tile_map


def make_object_layer(objects):
    layer = Mock(spec=ObjectLayer)
    layer.tiled_objects = objects
    return layer


def make_spawn_object(x, y, width=0, height=0, name="", properties=None):
    return SimpleNamespace(
        coordinates=SimpleNamespace(x=x, y=y),
        size=SimpleNamespace(width=width, height=height),
        name=name,
        properties=properties,
    )


def make_loader():
    return MapLoader(movement_system=None, player_state=None)


# --- _extract_spawns -----------------------------------------------------------


def test_extract_spawns_returns_empty_when_no_layer():
    loader = make_loader()
    tile_map = make_tile_map(layer=None)
    assert loader._extract_spawns(tile_map) == {}


def test_extract_spawns_keys_by_name_property():
    obj = make_spawn_object(10, 20, properties={"name": "gate"})
    tile_map = make_tile_map(make_object_layer([obj]), height=10, tile_height=16)

    spawns = make_loader()._extract_spawns(tile_map)

    assert "gate" in spawns
    x, y = spawns["gate"]
    assert x == 10 * 2.0
    assert y == (10 * 16 - 20) * 2.0


def test_extract_spawns_falls_back_to_tiled_object_name():
    obj = make_spawn_object(0, 0, name="south_door", properties={})
    tile_map = make_tile_map(make_object_layer([obj]))

    spawns = make_loader()._extract_spawns(tile_map)

    assert "south_door" in spawns


def test_extract_spawns_skips_object_with_no_name_at_all():
    obj = make_spawn_object(0, 0, name="", properties={})
    tile_map = make_tile_map(make_object_layer([obj]))

    assert make_loader()._extract_spawns(tile_map) == {}


def test_extract_spawns_handles_missing_properties():
    obj = make_spawn_object(0, 0, name="fallback", properties=None)
    tile_map = make_tile_map(make_object_layer([obj]))

    assert "fallback" in make_loader()._extract_spawns(tile_map)


# --- _build_npc_controller -------------------------------------------------------


def test_build_npc_controller_uses_collision_layer_when_present():
    loader = MapLoader(movement_system="ms", player_state="ps")
    tile_map = make_tile_map(width=20, height=10, tile_width=16, tile_height=16)
    scene = {"collision": ["wall_sprite"]}

    controller = loader._build_npc_controller(
        tile_map, cast(arcade.Scene, scene), npcs=arcade.SpriteList()
    )

    assert controller.collision_tiles == ["wall_sprite"]
    assert controller.movement_system == "ms"
    assert controller.player_state == "ps"
    assert controller.map_width == 20 * 16 * 2
    assert controller.map_height == 10 * 16 * 2


def test_build_npc_controller_falls_back_to_empty_spritelist_when_no_collision_layer():
    loader = make_loader()
    tile_map = make_tile_map()
    scene = {}  # scene["collision"] raises KeyError

    controller = loader._build_npc_controller(
        tile_map, cast(arcade.Scene, scene), npcs=arcade.SpriteList()
    )

    assert isinstance(controller.collision_tiles, arcade.SpriteList)
    assert len(controller.collision_tiles) == 0


# --- _extract_bush_tiles ---------------------------------------------------------


def test_extract_bush_tiles_builds_grid_set_from_sprites():
    from src.constants import TILE_SIZE

    sprite = SimpleNamespace(center_x=TILE_SIZE * 3, center_y=TILE_SIZE * 5)
    scene = {"bush": [sprite]}

    tiles = MapLoader._extract_bush_tiles(cast(arcade.Scene, scene))

    assert tiles == {(3, 5)}


def test_extract_bush_tiles_returns_empty_set_when_no_bush_layer():
    assert MapLoader._extract_bush_tiles(cast(arcade.Scene, {})) == set()
