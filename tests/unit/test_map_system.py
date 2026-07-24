"""Tests for the map system: MapRegistry, transition parsing, and MapManager
spawn resolution / lifecycle."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.world.map_registry import MapRegistry
from src.world.transition import Transition, parse_transition
from src.world.transition_layer import TransitionLayer, TransitionZone
from src.world.map_manager import MapManager


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
    assert (player.pixel_x, player.pixel_y) == (100.0, 200.0)
    assert mgr.current_map_id == "oldale_town"
    assert player.map_name == "oldale_town"
    # The id travels with the path so per-map state (collected items) can be
    # keyed without the loader re-deriving it.
    loader.load.assert_called_once_with("assets/map/oldale_town.tmx", "oldale_town")


def test_load_places_player_at_explicit_coords():
    mgr, player, _ = _manager({})
    mgr.load("test", (12.0, 34.0))
    assert (player.pixel_x, player.pixel_y) == (12.0, 34.0)


def test_unknown_spawn_falls_back_to_default():
    mgr, player, _ = _manager({"default": (5.0, 6.0)})
    mgr.load("test", "does_not_exist")
    assert (player.pixel_x, player.pixel_y) == (5.0, 6.0)


def test_none_spawn_uses_default_or_leaves_player():
    mgr, player, _ = _manager({"default": (7.0, 8.0)})
    mgr.load("test")  # spawn=None -> default
    assert (player.pixel_x, player.pixel_y) == (7.0, 8.0)

    mgr2, player2, _ = _manager({})  # no default -> player unchanged
    player2.pixel_x, player2.pixel_y = 99.0, 99.0
    mgr2.load("test")
    assert (player2.pixel_x, player2.pixel_y) == (99.0, 99.0)


def test_transition_uses_parsed_spawn():
    mgr, player, _ = _manager({"door": (1.0, 2.0)})
    mgr.transition(Transition(target_map="oldale_town", target_spawn="door"))
    assert (player.pixel_x, player.pixel_y) == (1.0, 2.0)


def test_warp_is_equivalent_to_load():
    mgr, player, _ = _manager({"heal": (3.0, 4.0)})
    mgr.warp("oldale_town/pokemon_center", "heal")
    assert (player.pixel_x, player.pixel_y) == (3.0, 4.0)
    assert mgr.current_map_id == "oldale_town/pokemon_center"


def test_hooks_and_unload_fire():
    loads, unloads = [], []
    mgr, player, _ = _manager(
        {"default": (0.0, 0.0)},
        on_load=lambda mid, loaded: loads.append(mid),
        on_unload=lambda mid, loaded: unloads.append(mid),
    )
    mgr.load("first")
    mgr.load("second")  # loading again unloads "first"
    assert loads == ["first", "second"]
    assert unloads == ["first"]
