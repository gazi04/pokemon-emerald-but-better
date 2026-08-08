"""Queryable ledge regions for one map.

A ledge is a one-way tile: you can hop *down* over it (in its authored
direction), but you can't climb back up. Approaching a ledge tile in its hop
direction jumps the player two tiles that way — over the ledge and onto the
ground beyond. From any other side it's impassable.

Two authoring styles, and a map may mix them:

  * **Tile layer** named `ledges` — paint ledge tiles straight onto the map.
    Direction comes from a `direction` property on the *tileset* tile (e.g. the
    south-edge tiles are tagged `down` in Tiles.tsx), exactly like the `bush`
    tile carries `pokemon`. Every map that paints those tiles then behaves
    correctly with no per-map setup.
  * **Object layer** named `ledges` — draw a rectangle along a whole ledge run
    and give the object a `direction` property. Handy for one-off ledges or
    overriding, without touching the tileset.

Tile sprites and gid objects both resolve through the same sprite hit-test;
rectangle objects are checked first.
"""

from dataclasses import dataclass, field

import arcade

from src.core.logger import get_logger
from src.tiled import find_object_layer

log = get_logger(__name__)

MAP_SCALE = 2.0
VALID_DIRECTIONS = frozenset({"up", "down", "left", "right"})


@dataclass(frozen=True)
class LedgeZone:
    """An axis-aligned ledge region in arcade world coordinates."""

    left: float
    bottom: float
    right: float
    top: float
    direction: str
    properties: dict = field(default_factory=dict)

    def contains(self, x: float, y: float) -> bool:
        return self.left <= x <= self.right and self.bottom <= y <= self.top


class LedgeLayer:
    def __init__(
        self,
        zones: list[LedgeZone],
        sprites: arcade.SpriteList | None = None,
    ):
        self._zones = zones
        self._sprites = sprites

    def __len__(self) -> int:
        return len(self._zones) + (len(self._sprites) if self._sprites else 0)

    def find(self, x: float, y: float) -> str | None:
        """The hop direction of the ledge at a world point, or None.

        Rectangle zones first, then the legacy gid sprite hit-test.
        """
        for zone in self._zones:
            if zone.contains(x, y):
                return zone.direction

        if self._sprites is not None:
            hit = arcade.get_sprites_at_point((x, y), self._sprites)
            if hit:
                return _normalize_direction(dict(hit[0].properties).get("direction"))

        return None

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_map(
        cls,
        tile_map: arcade.TileMap,
        scene: arcade.Scene,
        scale: float = MAP_SCALE,
    ) -> LedgeLayer:
        zones = cls._build_zones(tile_map, scale)
        sprites = cls._sprite_ledges(scene)
        log.debug(
            "Ledge layer: %d rectangle zones, %d tile/gid ledges",
            len(zones),
            len(sprites) if sprites else 0,
        )
        return cls(zones, sprites)

    @staticmethod
    def _build_zones(tile_map: arcade.TileMap, scale: float) -> list[LedgeZone]:
        layer = find_object_layer(tile_map, "ledges")
        zones: list[LedgeZone] = []
        if layer is None:
            return zones

        map_height_px = tile_map.height * tile_map.tile_height
        for obj in layer.tiled_objects:
            # Rectangle objects only; tile/gid ledges go through the sprite path.
            if getattr(obj, "gid", None):
                continue
            if not obj.size or obj.size.width <= 0 or obj.size.height <= 0:
                continue

            properties = dict(obj.properties or {})
            direction = _normalize_direction(properties.get("direction"))
            if direction is None:
                log.warning(
                    "Ledge object '%s' has no valid direction; ignoring", obj.name
                )
                continue

            # Tiled rectangle: top-left origin, y-down -> arcade y-up, scaled.
            left = obj.coordinates.x * scale
            right = (obj.coordinates.x + obj.size.width) * scale
            bottom = (map_height_px - (obj.coordinates.y + obj.size.height)) * scale
            top = (map_height_px - obj.coordinates.y) * scale
            zones.append(LedgeZone(left, bottom, right, top, direction, properties))
        return zones

    @staticmethod
    def _sprite_ledges(scene: arcade.Scene) -> arcade.SpriteList | None:
        """The `ledges` sprite list — a painted tile layer or gid objects.

        Both carry each tile's `direction` from the tileset definition, read at
        query time in `find`.
        """
        try:
            return scene["ledges"]
        except KeyError:
            return None


def _normalize_direction(value) -> str | None:
    """Coerce a Tiled property to a valid hop direction, or None."""
    if value is None:
        return None
    direction = str(value).strip().lower()
    return direction if direction in VALID_DIRECTIONS else None
