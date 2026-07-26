"""Queryable transition regions for one map.

Transitions are authored on a Tiled `transitions` **object layer**. Each object
is an independent region with its own `target_map` / `target_spawn` properties —
so a map can have as many distinct doors/warps as you like, unlike a tile layer
(which shares one property set per tile type).

Two authoring styles are supported:
  * **Rectangle objects** (preferred) — drawn as a region, detected by
    point-in-rect. Any size, any number, each with its own properties.
  * **Tile/gid objects** (legacy doors) — kept working via the sprite hit-test
    fallback so existing maps need no migration.
"""

from dataclasses import dataclass, field

import arcade

from src.core.logger import get_logger
from src.tiled import find_object_layer

log = get_logger(__name__)

MAP_SCALE = 2.0


@dataclass(frozen=True)
class TransitionZone:
    """An axis-aligned transition region in arcade world coordinates."""

    left: float
    bottom: float
    right: float
    top: float
    properties: dict = field(default_factory=dict)

    def contains(self, x: float, y: float) -> bool:
        return self.left <= x <= self.right and self.bottom <= y <= self.top


class TransitionLayer:
    def __init__(
        self,
        zones: list[TransitionZone],
        sprites: arcade.SpriteList | None = None,
    ):
        self._zones = zones
        self._sprites = sprites

    def __len__(self) -> int:
        return len(self._zones) + (len(self._sprites) if self._sprites else 0)

    def find(self, x: float, y: float) -> dict | None:
        """Return the transition properties at a world point, or None.

        Rectangle zones are checked first; legacy gid doors fall back to the
        sprite hit-test.
        """
        for zone in self._zones:
            if zone.contains(x, y):
                return zone.properties

        if self._sprites is not None:
            hit = arcade.get_sprites_at_point((x, y), self._sprites)
            if hit:
                return dict(hit[0].properties)

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
    ) -> TransitionLayer:
        zones = cls._build_zones(tile_map, scale)
        sprites = cls._legacy_sprites(scene)
        log.debug(
            "Transition layer: %d rectangle zones, %d legacy gid doors",
            len(zones),
            len(sprites) if sprites else 0,
        )
        return cls(zones, sprites)

    @staticmethod
    def _build_zones(tile_map: arcade.TileMap, scale: float) -> list[TransitionZone]:
        layer = find_object_layer(tile_map, "transitions")
        zones: list[TransitionZone] = []
        if layer is None:
            return zones

        map_height_px = tile_map.height * tile_map.tile_height
        for obj in layer.tiled_objects:
            # Rectangle objects only; tile/gid doors go through the sprite path.
            if getattr(obj, "gid", None):
                continue
            if not obj.size or obj.size.width <= 0 or obj.size.height <= 0:
                continue

            # Tiled rectangle: top-left origin, y-down -> arcade y-up, scaled.
            left = obj.coordinates.x * scale
            right = (obj.coordinates.x + obj.size.width) * scale
            bottom = (map_height_px - (obj.coordinates.y + obj.size.height)) * scale
            top = (map_height_px - obj.coordinates.y) * scale
            zones.append(
                TransitionZone(left, bottom, right, top, dict(obj.properties or {}))
            )
        return zones

    @staticmethod
    def _legacy_sprites(scene: arcade.Scene) -> arcade.SpriteList | None:
        try:
            return scene["transitions"]
        except KeyError:
            return None
