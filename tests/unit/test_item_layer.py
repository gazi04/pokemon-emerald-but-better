"""Overworld item pickups: locating them, taking them, and keeping them gone."""

from src.world.item_layer import ItemLayer, OverworldItem
import pytest


class FakeSprite:
    """Stands in for the arcade tile-object sprite of a ground item."""

    def __init__(self, x=0.0, y=0.0, properties=None, size=32):
        self.center_x = x
        self.center_y = y
        self.properties = properties or {}
        self.removed = False
        self._half = size / 2

    def collides_with_point(self, point):
        px, py = point
        return (
            abs(px - self.center_x) <= self._half
            and abs(py - self.center_y) <= self._half
        )

    def remove_from_sprite_lists(self):
        self.removed = True


class FakeScene:
    """Minimal arcade.Scene stand-in: name -> sprite list, KeyError if absent."""

    def __init__(self, layers):
        self._layers = layers

    def __getitem__(self, name):
        return self._layers[name]


def make_item(key="m:potion", item_id="potion", x=0.0, y=0.0):
    # type: ignore
    return OverworldItem(key=key, item_id=item_id, sprite=FakeSprite(x, y))  # type: ignore


# --- finding ----------------------------------------------------------------


def test_find_returns_item_on_that_tile():
    item = make_item(x=100.0, y=100.0)
    layer = ItemLayer([item])

    assert layer.find(100.0, 100.0) is item
    assert layer.find(112.0, 108.0) is item  # anywhere within the tile


def test_find_returns_none_off_the_item():
    layer = ItemLayer([make_item(x=100.0, y=100.0)])
    assert layer.find(400.0, 100.0) is None


def test_find_by_key():
    item = make_item(key="town:elixir")
    layer = ItemLayer([item])

    assert layer.find_by_key("town:elixir") is item
    assert layer.find_by_key("town:nothing") is None


def test_empty_layer_finds_nothing():
    assert ItemLayer().find(0.0, 0.0) is None
    assert len(ItemLayer()) == 0


# --- collecting -------------------------------------------------------------


def test_collect_removes_item_from_layer_and_scene():
    item = make_item(x=50.0, y=50.0)
    layer = ItemLayer([item])

    layer.collect(item)

    assert len(layer) == 0
    assert layer.find(50.0, 50.0) is None  # no longer blocks the tile
    assert item.sprite.removed  # stops rendering  # type: ignore


def test_collect_is_idempotent():
    item = make_item()
    layer = ItemLayer([item])

    layer.collect(item)
    layer.collect(item)  # a double-trigger must not explode

    assert len(layer) == 0


# --- loading from a map -----------------------------------------------------


def test_from_map_reads_item_id_from_properties():
    sprite = FakeSprite(10.0, 20.0, {"item_id": "potion", "name": "porch_potion"})
    layer = ItemLayer.from_map(FakeScene({"items": [sprite]}), "littleroot")  # type: ignore

    item = layer.find(10.0, 20.0)
    if item is None:
        pytest.fail("Couldnt find the item.")

    assert item.item_id == "potion"
    assert item.key == "littleroot:porch_potion"


def test_from_map_skips_already_collected_items():
    sprite = FakeSprite(10.0, 20.0, {"item_id": "potion", "name": "porch_potion"})
    layer = ItemLayer.from_map(
        FakeScene({"items": [sprite]}),  # type: ignore
        "littleroot",
        collected={"littleroot:porch_potion"},
    )

    assert len(layer) == 0
    assert sprite.removed  # pulled from the scene so it never renders


def test_from_map_ignores_objects_without_item_id():
    sprite = FakeSprite(properties={"name": "decoration"})
    layer = ItemLayer.from_map(FakeScene({"items": [sprite]}), "littleroot")  # type: ignore
    assert len(layer) == 0


def test_from_map_without_items_layer_is_empty():
    assert len(ItemLayer.from_map(FakeScene({}), "littleroot")) == 0  # type: ignore


def test_key_falls_back_to_position_when_unnamed():
    sprite = FakeSprite(64.0, 96.0, {"item_id": "potion"})
    layer = ItemLayer.from_map(FakeScene({"items": [sprite]}), "littleroot")  # type: ignore

    item = layer.find(64.0, 96.0)
    if item is None:
        pytest.fail("Couldnt find the item")

    assert item.key == "littleroot:64,96"


def test_keys_are_scoped_per_map():
    def build(map_id):
        sprite = FakeSprite(0.0, 0.0, {"item_id": "potion", "name": "ball"})
        return ItemLayer.from_map(FakeScene({"items": [sprite]}), map_id)  # type: ignore

    item1 = build("littleroot").find(0.0, 0.0)
    item2 = build("oldale").find(0.0, 0.0)

    if item1 is None or item2 is None:
        pytest.fail("Couldnt find the item")

    assert item1.key != item2.key
