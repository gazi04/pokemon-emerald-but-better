"""Tests for the map system: MapRegistry, transition parsing, and MapManager
spawn resolution / lifecycle."""

from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, Mock

import arcade
import pytest
from pytiled_parser import ObjectLayer

from src.world.map_registry import MapRegistry
from src.world.transition import Transition, parse_transition
from src.world.transition_layer import TransitionLayer, TransitionZone
from src.world.map_manager import SPAWN_Y_OFFSET, MapManager


# --- MapRegistry -----------------------------------------------------------


def test_registry_path_and_id_round_trip():
    reg = MapRegistry("assets/map")
    assert (
        reg.path_for("oldale_town/pokemon_center")
        == "assets/map/oldale_town/pokemon_center.tmx"
    )
    assert (
        reg.id_from_path("assets/map/oldale_town/pokemon_center.tmx")
        == "oldale_town/pokemon_center"
    )
    # idempotent on an already-clean id
    assert reg.id_from_path("littleroot_town") == "littleroot_town"


def test_registry_accepts_full_path_as_ref():
    reg = MapRegistry("assets/map")
    assert reg.resolve("assets/map/test.tmx") == "test"


def test_registry_aliases():
    reg = MapRegistry("assets/map", aliases={"fly:oldale": "oldale_town"})
    assert reg.resolve("fly:oldale") == "oldale_town"
    assert reg.path_for("fly:oldale") == "assets/map/oldale_town.tmx"
    reg.register_alias("home", "little_root_town/home")
    assert reg.resolve("home") == "little_root_town/home"


# --- transition parsing ----------------------------------------------------


def test_parse_transition_named_spawn():
    t = parse_transition({"target_map": "oldale_town", "target_spawn": "south_gate"})
    assert t.target_map == "oldale_town"
    assert t.spawn == "south_gate"
    assert t.target_position is None


def test_parse_transition_legacy_coords():
    t = parse_transition({"destination map": "test", "x": 366, "y": 205})
    assert t.target_map == "test"
    assert t.target_spawn is None
    assert t.spawn == (366.0, 205.0)


def test_parse_transition_missing_map_raises():
    with pytest.raises(KeyError):
        parse_transition({"x": 1, "y": 2})


# --- TransitionLayer (rectangle regions) -----------------------------------


def test_zone_contains():
    z = TransitionZone(left=100, bottom=100, right=200, top=200, properties={"k": "v"})
    assert z.contains(150, 150)
    assert z.contains(100, 100) and z.contains(200, 200)  # edges inclusive
    assert not z.contains(250, 150)


def test_layer_finds_rectangle_zone_first():
    z1 = TransitionZone(0, 0, 50, 50, {"target_map": "a"})
    z2 = TransitionZone(50, 50, 100, 100, {"target_map": "b"})
    layer = TransitionLayer([z1, z2], sprites=None)
    first, second = layer.find(10, 10), layer.find(75, 75)
    assert first is not None and second is not None
    assert first["target_map"] == "a"
    assert second["target_map"] == "b"
    assert layer.find(300, 300) is None
    assert len(layer) == 2


def test_layer_empty_returns_none():
    assert TransitionLayer([], sprites=None).find(5, 5) is None


# --- TransitionLayer construction (_build_zones / from_map / legacy sprites) --


def make_tile_map(layer=None, height=10, tile_height=16):
    tile_map = MagicMock()
    tile_map.get_tilemap_layer.return_value = layer
    tile_map.height = height
    tile_map.tile_height = tile_height
    return tile_map


def make_object_layer(objects):
    layer = Mock(spec=ObjectLayer)
    layer.tiled_objects = objects
    return layer


def make_rect_object(x, y, width, height, properties=None, gid=None):
    return SimpleNamespace(
        coordinates=SimpleNamespace(x=x, y=y),
        size=SimpleNamespace(width=width, height=height),
        properties=properties or {},
        gid=gid,
    )


def test_build_zones_converts_tiled_rect_to_world_coords():
    obj = make_rect_object(0, 0, 32, 32, properties={"target_map": "oldale_town"})
    tile_map = make_tile_map(make_object_layer([obj]), height=10, tile_height=16)

    zones = TransitionLayer._build_zones(tile_map, scale=2.0)

    assert len(zones) == 1
    zone = zones[0]
    # map_height_px = 10*16=160; top-left origin, y-down -> arcade y-up, scaled 2x.
    assert (zone.left, zone.right) == (0.0, 64.0)
    assert (zone.bottom, zone.top) == (256.0, 320.0)
    assert zone.properties == {"target_map": "oldale_town"}


def test_build_zones_skips_gid_objects():
    obj = make_rect_object(0, 0, 32, 32, gid=5)
    tile_map = make_tile_map(make_object_layer([obj]))
    assert TransitionLayer._build_zones(tile_map, scale=2.0) == []


def test_build_zones_skips_zero_size_objects():
    obj = make_rect_object(0, 0, 0, 0)
    tile_map = make_tile_map(make_object_layer([obj]))
    assert TransitionLayer._build_zones(tile_map, scale=2.0) == []


def test_build_zones_returns_empty_when_no_transitions_layer():
    tile_map = make_tile_map(layer=None)
    assert TransitionLayer._build_zones(tile_map, scale=2.0) == []


def test_legacy_sprites_returns_scene_layer_when_present():
    sprites = ["fake_sprite_list"]
    scene = {"transitions": sprites}
    assert TransitionLayer._legacy_sprites(cast(arcade.Scene, scene)) == sprites


def test_legacy_sprites_returns_none_when_absent():
    assert TransitionLayer._legacy_sprites(cast(arcade.Scene, {})) is None


def test_from_map_builds_zones_and_legacy_sprites():
    obj = make_rect_object(0, 0, 32, 32, properties={"target_map": "a"})
    tile_map = make_tile_map(make_object_layer([obj]))
    scene = cast(arcade.Scene, {"transitions": ["door_sprite"]})

    layer = TransitionLayer.from_map(tile_map, scene, scale=2.0)

    assert len(layer._zones) == 1
    assert layer._sprites == ["door_sprite"]
    assert len(layer) == 2


# --- MapManager ------------------------------------------------------------


def _loaded(spawns):
    return SimpleNamespace(
        tile_map=None,
        scene=None,
        npcs=MagicMock(),
        npc_controller=None,
        bush_tiles=set(),
        spawns=spawns,
    )


def _manager(spawns, on_load=None, on_unload=None):
    loader = MagicMock()
    loader.load.return_value = _loaded(spawns)
    registry = MapRegistry("assets/map")
    player = SimpleNamespace(pixel_x=0.0, pixel_y=0.0, map_name="")
    mgr = MapManager(loader, registry, player, on_load=on_load, on_unload=on_unload)
    return mgr, player, loader


def test_load_places_player_at_named_spawn():
    mgr, player, loader = _manager({"gate": (100.0, 200.0)})
    mgr.load("oldale_town", "gate")
    assert (player.pixel_x, player.pixel_y) == (100.0, 200.0 + SPAWN_Y_OFFSET)
    assert mgr.current_map_id == "oldale_town"
    assert player.map_name == "oldale_town"
    loader.load.assert_called_once_with("assets/map/oldale_town.tmx")


def test_load_places_player_at_explicit_coords():
    mgr, player, _ = _manager({})
    mgr.load("test", (12.0, 34.0))
    assert (player.pixel_x, player.pixel_y) == (12.0, 34.0 + SPAWN_Y_OFFSET)


def test_unknown_spawn_falls_back_to_default():
    mgr, player, _ = _manager({"default": (5.0, 6.0)})
    mgr.load("test", "does_not_exist")
    assert (player.pixel_x, player.pixel_y) == (5.0, 6.0 + SPAWN_Y_OFFSET)


def test_none_spawn_uses_default_or_leaves_player():
    mgr, player, _ = _manager({"default": (7.0, 8.0)})
    mgr.load("test")  # spawn=None -> default
    assert (player.pixel_x, player.pixel_y) == (7.0, 8.0 + SPAWN_Y_OFFSET)

    mgr2, player2, _ = _manager({})  # no default -> player unchanged
    player2.pixel_x, player2.pixel_y = 99.0, 99.0
    mgr2.load("test")
    assert (player2.pixel_x, player2.pixel_y) == (99.0, 99.0)


def test_transition_uses_parsed_spawn():
    mgr, player, _ = _manager({"door": (1.0, 2.0)})
    mgr.transition(Transition(target_map="oldale_town", target_spawn="door"))
    assert (player.pixel_x, player.pixel_y) == (1.0, 2.0 + SPAWN_Y_OFFSET)


def test_warp_is_equivalent_to_load():
    mgr, player, _ = _manager({"heal": (3.0, 4.0)})
    mgr.warp("oldale_town/pokemon_center", "heal")
    assert (player.pixel_x, player.pixel_y) == (3.0, 4.0 + SPAWN_Y_OFFSET)
    assert mgr.current_map_id == "oldale_town/pokemon_center"


def test_hooks_and_unload_fire():
    loads, unloads = [], []
    mgr, _player, _ = _manager(
        {"default": (0.0, 0.0)},
        on_load=lambda mid, loaded: loads.append(mid),
        on_unload=lambda mid, loaded: unloads.append(mid),
    )
    mgr.load("first")
    mgr.load("second")  # loading again unloads "first"
    assert loads == ["first", "second"]
    assert unloads == ["first"]
