"""Tests for ShopView's stock selection and amount arithmetic.

`ShopView.__init__` needs an arcade window and a parsed .tmx layout, so these
build the view via `__new__` and set only the attributes the methods under test
read — the pattern established in test_battle_view.py.

The bugs these cover: the mart listed every item in the game, ten of which are
priced 0, so scrolling the amount on one divided by zero; and the same items
could then be bought for nothing.
"""

from unittest.mock import MagicMock

import pytest

from src.model.static.item import ItemSpecies
from src.states.shop_view import ShopView


def _item(name: str, price: int) -> ItemSpecies:
    return ItemSpecies(
        {
            "name": name,
            "description": "",
            "price": price,
            "category": "medicine",
            "holdable": False,
            "effects": [],
        }
    )


CATALOGUE = {
    "potion": _item("potion", 300),
    "super potion": _item("super potion", 700),
    "sitrus berry": _item("sitrus berry", 0),
    "life orb": _item("life orb", 0),
}


@pytest.fixture
def shop(player_manager):
    view = ShopView.__new__(ShopView)
    view.player_manager = player_manager
    view.ui = MagicMock()
    view._mode = "amount"
    view._amount = 1
    view._item_index = 0
    view.items = ShopView.purchasable(CATALOGUE)
    view._item_names = list(view.items.keys())
    return view


def test_zero_priced_items_are_not_stocked(shop):
    """price: 0 means 'not for sale' in the data — those items are found or
    given, never bought."""
    assert shop._item_names == ["potion", "super potion"]
    assert "sitrus berry" not in shop.items
    assert "life orb" not in shop.items


def test_purchasable_keeps_every_priced_item():
    stocked = ShopView.purchasable(CATALOGUE)

    assert set(stocked) == {"potion", "super potion"}
    assert all(item.price > 0 for item in stocked.values())


def test_scrolling_amount_on_a_free_item_does_not_divide_by_zero(shop, player_manager):
    """The crash: max_affordable = money // price. Even if a zero-priced item
    reaches the amount screen through some other path, it must not raise."""
    player_manager.player.money = 1000
    free = _item("sitrus berry", 0)

    shop._handle_amount_step(free, +1)

    assert shop._amount == 1


def test_amount_never_drops_to_zero_when_broke(shop, player_manager):
    """Pressing UP with too little money used to clamp to max_affordable == 0,
    and buying then added a 0-count stack."""
    player_manager.player.money = 10  # cannot afford one 300-cost potion

    shop._handle_amount_step(CATALOGUE["potion"], +1)

    assert shop._amount == 1


def test_amount_rises_up_to_what_the_player_can_afford(shop, player_manager):
    player_manager.player.money = 1000  # three potions at 300

    for _ in range(5):
        shop._handle_amount_step(CATALOGUE["potion"], +1)

    assert shop._amount == 3
