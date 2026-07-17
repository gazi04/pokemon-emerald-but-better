"""Shared helpers for reading Tiled object layers.

`arcade.TileMap.get_tilemap_layer` returns `Layer | None`, and only the
ObjectLayer subclass carries `tiled_objects`. Both facts have to be handled at
every call site, so they're handled once here instead. Lives at the top level
(like `constants`) because ui/, states/ and world/ all read .tmx layers.
"""

import arcade
from pytiled_parser import ObjectLayer


def find_object_layer(tile_map: arcade.TileMap, name: str) -> ObjectLayer | None:
    """Return the named object layer, or None if the map doesn't define one.

    For layers that are genuinely optional — e.g. legacy maps with no 'spawns'.
    """
    layer = tile_map.get_tilemap_layer(name)
    return layer if isinstance(layer, ObjectLayer) else None


def object_layer(tile_map: arcade.TileMap, name: str) -> ObjectLayer:
    """Return the named object layer, or raise naming the one that's missing.

    For layers the caller requires: every call site passes a literal name that
    the shipped .tmx defines, so a miss means the asset drifted — fail at the
    lookup saying which layer, rather than on a None deref further down.
    """
    layer = find_object_layer(tile_map, name)
    if layer is None:
        raise KeyError(f"Map has no object layer '{name}'")
    return layer
