"""Pick-up-able items lying in the overworld.

Authored in Tiled as **tile objects** on an `items` object layer, each carrying
an `item_id` property naming an entry in data/items.json. The tile object's art
is whatever Poké Ball tile you drew, so the layer renders itself — this module
only answers "is there an item on this tile?" and removes it once taken.

Collected items are remembered by key so they never respawn.
"""

from dataclasses import dataclass
from collections.abc import Iterable

import arcade

from src.core.logger import get_logger

log = get_logger(__name__)


@dataclass
class OverworldItem:
    """One pickup: what it gives, where it is, and how it's remembered."""

    key: str
    item_id: str
    sprite: arcade.Sprite

    @property
    def position(self) -> tuple[float, float]:
        return (self.sprite.center_x, self.sprite.center_y)


class ItemLayer:
    """The uncollected items on the current map."""

    def __init__(self, items: Iterable[OverworldItem] | None = None):
        self._items: list[OverworldItem] = list(items or [])

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def find(self, x: float, y: float) -> OverworldItem | None:
        """The item whose tile contains (x, y), if any."""
        for item in self._items:
            if item.sprite.collides_with_point((x, y)):
                return item
        return None

    def find_by_key(self, key: str) -> OverworldItem | None:
        """The uncollected item with this key, if it's still on the map."""
        for item in self._items:
            if item.key == key:
                return item
        return None

    def collect(self, item: OverworldItem) -> None:
        """Take the item: it stops rendering and stops blocking the tile."""
        if item in self._items:
            self._items.remove(item)
        item.sprite.remove_from_sprite_lists()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @classmethod
    def from_map(
        cls,
        scene: arcade.Scene,
        map_id: str,
        collected: set[str] | None = None,
    ) -> ItemLayer:
        """Build from the scene's `items` sprite list.

        Arcade already turned the layer's tile objects into positioned sprites
        carrying their Tiled properties, so we read those rather than walking
        the raw objects again. Anything already collected is dropped from the
        scene here, which is what stops it reappearing on re-entry.
        """
        collected = collected or set()

        try:
            sprites = scene["items"]
        except KeyError:
            return cls()

        items: list[OverworldItem] = []
        for sprite in list(sprites):
            properties = dict(getattr(sprite, "properties", None) or {})
            item_id = properties.get("item_id")

            if not item_id:
                log.warning(
                    "Item object on '%s' has no item_id property; ignoring", map_id
                )
                continue

            key = cls.make_key(map_id, properties, sprite)
            if key in collected:
                sprite.remove_from_sprite_lists()
                continue

            items.append(OverworldItem(key=key, item_id=item_id, sprite=sprite))

        return cls(items)

    @staticmethod
    def make_key(map_id: str, properties: dict, sprite: arcade.Sprite) -> str:
        """A stable id for "this specific item on this map".

        Prefers the Tiled object's name so the key survives nudging the object
        in the editor; falls back to its tile position when unnamed.
        """
        name = properties.get("name")
        if name:
            return f"{map_id}:{name}"
        return f"{map_id}:{round(sprite.center_x)},{round(sprite.center_y)}"
