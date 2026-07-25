"""Ledge regions: locating the hop direction, and rejecting bad authoring."""

import arcade
import pytest

from src.constants import TILE_SIZE
from src.world.ledge_layer import LedgeLayer, LedgeZone, _normalize_direction


# --- LedgeZone / find -------------------------------------------------------


def test_zone_contains():
    zone = LedgeZone(left=0, bottom=0, right=64, top=64, direction="down")
    assert zone.contains(32, 32)
    assert zone.contains(0, 0) and zone.contains(64, 64)  # edges inclusive
    assert not zone.contains(100, 32)


def test_find_returns_direction_of_the_zone():
    layer = LedgeLayer(
        [
            LedgeZone(0, 0, 32, 32, "down"),
            LedgeZone(32, 0, 64, 32, "left"),
        ]
    )
    assert layer.find(16, 16) == "down"
    assert layer.find(48, 16) == "left"
    assert layer.find(200, 200) is None


def test_empty_layer_finds_nothing():
    assert LedgeLayer([]).find(5, 5) is None
    assert len(LedgeLayer([])) == 0


# --- direction normalization ------------------------------------------------


def test_normalize_direction_accepts_cardinals():
    for value in ("up", "down", "left", "right"):
        assert _normalize_direction(value) == value


def test_normalize_direction_is_case_and_space_insensitive():
    assert _normalize_direction(" Down ") == "down"
    assert _normalize_direction("LEFT") == "left"


def test_normalize_direction_rejects_junk():
    assert _normalize_direction("diagonal") is None
    assert _normalize_direction("") is None
    assert _normalize_direction(None) is None


# --- painted tile layer (direction from the tileset tile) -------------------


@pytest.fixture(scope="module")
def window():
    win = arcade.Window(60, 60, "test", visible=False)
    yield win
    win.close()


def _sprite(x, y, direction):
    sprite = arcade.SpriteSolidColor(TILE_SIZE, TILE_SIZE, color=arcade.color.WHITE)
    sprite.center_x, sprite.center_y = x, y
    # Mirrors what arcade attaches from the tileset tile definition.
    sprite.properties = {"tile_id": 1415, "direction": direction}
    return sprite


def test_tile_layer_direction_comes_from_the_sprite(window):
    ledge = _sprite(48, 48, "down")
    sprites = arcade.SpriteList(use_spatial_hash=True)
    sprites.append(ledge)

    layer = LedgeLayer(zones=[], sprites=sprites)
    assert layer.find(48, 48) == "down"
    assert layer.find(500, 500) is None
    assert len(layer) == 1


def test_tile_without_a_direction_property_is_not_a_ledge(window):
    plain = arcade.SpriteSolidColor(TILE_SIZE, TILE_SIZE, color=arcade.color.WHITE)
    plain.center_x, plain.center_y = 48, 48
    plain.properties = {"tile_id": 1415}  # no direction tagged
    sprites = arcade.SpriteList(use_spatial_hash=True)
    sprites.append(plain)

    assert LedgeLayer(zones=[], sprites=sprites).find(48, 48) is None


def test_rectangle_zone_wins_over_a_sprite_at_the_same_point(window):
    sprites = arcade.SpriteList(use_spatial_hash=True)
    sprites.append(_sprite(48, 48, "down"))
    layer = LedgeLayer(
        zones=[LedgeZone(32, 32, 64, 64, "left")], sprites=sprites
    )

    assert layer.find(48, 48) == "left"  # object-layer override
