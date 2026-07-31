"""Tests for src.tiled: shared Tiled object-layer lookup helpers."""

from unittest.mock import MagicMock, Mock

import pytest
from pytiled_parser import ObjectLayer

from src.tiled import find_object_layer, object_layer


def make_tile_map(layer=None):
    tile_map = MagicMock()
    tile_map.get_tilemap_layer.return_value = layer
    return tile_map


def test_find_object_layer_returns_object_layer_when_present():
    layer = Mock(spec=ObjectLayer)
    tile_map = make_tile_map(layer)

    assert find_object_layer(tile_map, "spawns") is layer
    tile_map.get_tilemap_layer.assert_called_once_with("spawns")


def test_find_object_layer_returns_none_when_missing():
    tile_map = make_tile_map(None)
    assert find_object_layer(tile_map, "spawns") is None


def test_find_object_layer_returns_none_for_non_object_layer():
    """A tile layer (not an ObjectLayer) at that name doesn't count."""
    tile_map = make_tile_map(MagicMock())  # plain mock, not spec'd as ObjectLayer
    assert find_object_layer(tile_map, "collision") is None


def test_object_layer_returns_the_layer_when_present():
    layer = Mock(spec=ObjectLayer)
    tile_map = make_tile_map(layer)
    assert object_layer(tile_map, "transitions") is layer


def test_object_layer_raises_naming_the_missing_layer():
    tile_map = make_tile_map(None)
    with pytest.raises(KeyError, match="transitions"):
        object_layer(tile_map, "transitions")
