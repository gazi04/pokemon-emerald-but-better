"""Tests for parse_battle_layout: Tiled object-layer geometry -> tile bounds.

`arcade.tilemap.load_tilemap` and `find_object_layer` are both monkeypatched
so this runs without a real .tmx file or GL context.
"""

from types import SimpleNamespace

import src.ui.layout_parser as layout_parser


def make_obj(name, x, y, w, h):
    return SimpleNamespace(
        name=name,
        coordinates=SimpleNamespace(x=x, y=y),
        size=SimpleNamespace(width=w, height=h),
    )


def make_tilemap(layers, map_height_tiles=10, tile_size=32):
    tiled_map = SimpleNamespace(
        map_size=SimpleNamespace(height=map_height_tiles),
        tile_size=SimpleNamespace(height=tile_size),
        layers=[SimpleNamespace(name=name) for name in layers],
    )
    return SimpleNamespace(tiled_map=tiled_map)


def test_extracts_bounds_from_a_single_object_layer(monkeypatch):
    tilemap = make_tilemap(["obstacles"], map_height_tiles=10, tile_size=32)
    monkeypatch.setattr(layout_parser.arcade.tilemap, "load_tilemap", lambda p: tilemap)

    obj = make_obj("wall_1", x=32, y=64, w=64, h=32)
    obj_layer = SimpleNamespace(tiled_objects=[obj])
    monkeypatch.setattr(layout_parser, "find_object_layer", lambda tm, name: obj_layer)

    bounds = layout_parser.parse_battle_layout("dummy.tmx")

    # raw_map_height = 10 * 32 = 320; y = (320 - 64) / 32 = 8
    assert bounds == {"wall_1": {"x": 1, "y": 8, "w": 2, "h": 1}}


def test_skips_layers_that_are_not_object_layers(monkeypatch):
    tilemap = make_tilemap(["tiles", "obstacles"], map_height_tiles=5, tile_size=32)
    monkeypatch.setattr(layout_parser.arcade.tilemap, "load_tilemap", lambda p: tilemap)

    obj = make_obj("spawn", x=0, y=0, w=32, h=32)
    obj_layer = SimpleNamespace(tiled_objects=[obj])

    def fake_find(tm, name):
        return obj_layer if name == "obstacles" else None

    monkeypatch.setattr(layout_parser, "find_object_layer", fake_find)

    bounds = layout_parser.parse_battle_layout("dummy.tmx")

    assert bounds == {"spawn": {"x": 0, "y": 5, "w": 1, "h": 1}}


def test_multiple_objects_in_one_layer_all_captured(monkeypatch):
    tilemap = make_tilemap(["obstacles"], map_height_tiles=4, tile_size=32)
    monkeypatch.setattr(layout_parser.arcade.tilemap, "load_tilemap", lambda p: tilemap)

    obj_a = make_obj("a", x=0, y=0, w=32, h=32)
    obj_b = make_obj("b", x=32, y=32, w=32, h=32)
    obj_layer = SimpleNamespace(tiled_objects=[obj_a, obj_b])
    monkeypatch.setattr(layout_parser, "find_object_layer", lambda tm, name: obj_layer)

    bounds = layout_parser.parse_battle_layout("dummy.tmx")

    assert set(bounds.keys()) == {"a", "b"}


def test_no_object_layers_returns_empty_bounds(monkeypatch):
    tilemap = make_tilemap(["tiles"], map_height_tiles=4, tile_size=32)
    monkeypatch.setattr(layout_parser.arcade.tilemap, "load_tilemap", lambda p: tilemap)
    monkeypatch.setattr(layout_parser, "find_object_layer", lambda tm, name: None)

    bounds = layout_parser.parse_battle_layout("dummy.tmx")

    assert bounds == {}
