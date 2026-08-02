"""Tests for BagView's non-drawing logic: item list rendering, selection
scrolling, and the interact/throw-pokeball dispatch.

`__init__` needs a real arcade window and parsed .tmx layout, so these
construct via `__new__` and set only what each method reads — same pattern
as tests/unit/test_battle_view.py.
"""

from typing import Any
from unittest.mock import MagicMock


from src.constants import MAX_VISIBLE_ITEMS
from src.enums.item_category import ItemCategory
from src.model.save.player import ItemStack
from src.states.bag_view import BagView
import src.states.bag_view as bag_view_module


def make_view(data_loader, inventory=None, bag_index=0) -> Any:
    view: Any = BagView.__new__(BagView)
    view.data_loader = data_loader
    view.ui = MagicMock()
    view.ui.itemLabels = [MagicMock() for _ in range(MAX_VISIBLE_ITEMS)]
    inventory = inventory if inventory is not None else []
    view.bagSystem = MagicMock()
    view.bagSystem.get_items.return_value = {ItemCategory.MEDICINE: inventory}
    view.bag = {}
    view.current_inventory = inventory
    view.bagIndex = bag_index
    view.currentIndex = 0
    view.topVisibleIndex = 0
    view.previous_view = MagicMock()
    view.battle_system = None
    view.window = MagicMock()
    return view


def potions(n):
    return [
        ItemStack(name="potion", count=c, category="medicine") for c in range(1, n + 1)
    ]


def test_update_item_formats_label_with_count(data_loader):
    view = make_view(data_loader, inventory=potions(1))

    view.update_item()

    assert view.ui.itemLabels[0].text == "POTION         x1"


def test_update_item_shows_bare_name_when_count_zero(data_loader):
    stack = ItemStack(name="potion", count=0, category="medicine")
    view = make_view(data_loader, inventory=[stack])

    view.update_item()

    assert view.ui.itemLabels[0].text == "POTION"


def test_update_item_empty_inventory_shows_placeholder_text(data_loader):
    view = make_view(data_loader, inventory=[])

    view.update_item()

    view.ui.set_text.assert_called_once_with("There isn't any items.")
    assert view.currentIndex == 0


def test_update_item_clamps_current_index_when_list_shrinks(data_loader):
    view = make_view(data_loader, inventory=potions(3))
    view.currentIndex = 2

    view.bagSystem.get_items.return_value = {ItemCategory.MEDICINE: potions(1)}
    view.update_item()

    assert view.currentIndex == 0


def test_update_item_known_item_shows_its_description(data_loader):
    view = make_view(data_loader, inventory=potions(1))

    view.update_item()

    view.ui.set_text.assert_called_once_with("Restores 20 HP.")


def test_update_item_unknown_item_shows_fallback_text(data_loader):
    stack = ItemStack(name="mysterious_egg", count=1, category="medicine")
    view = make_view(data_loader, inventory=[stack])

    view.update_item()

    view.ui.set_text.assert_called_once_with("Unknown item description.")


def test_move_selection_out_of_bounds_is_a_noop(data_loader):
    view = make_view(data_loader, inventory=potions(2))

    view._move_selection(-1)

    assert view.currentIndex == 0


def test_move_selection_advances_within_bounds(data_loader):
    view = make_view(data_loader, inventory=potions(2))

    view._move_selection(1)

    assert view.currentIndex == 1


def test_move_selection_scrolls_window_forward_past_visible_items(data_loader):
    view = make_view(data_loader, inventory=potions(MAX_VISIBLE_ITEMS + 2))
    view.currentIndex = MAX_VISIBLE_ITEMS - 1

    view._move_selection(1)

    assert view.topVisibleIndex == 1


def test_move_selection_scrolls_window_backward(data_loader):
    view = make_view(data_loader, inventory=potions(MAX_VISIBLE_ITEMS + 2))
    view.currentIndex = 1
    view.topVisibleIndex = 1

    view._move_selection(-1)

    assert view.topVisibleIndex == 0


def test_interact_medicine_tab_opens_item_menu(data_loader, monkeypatch):
    view = make_view(data_loader, inventory=potions(1), bag_index=0)
    view.current_inventory = potions(1)
    view._open_item_menu = MagicMock()

    view._on_interact()

    view._open_item_menu.assert_called_once()


def test_interact_pokeball_tab_in_wild_battle_throws_pokeball(data_loader):
    view = make_view(data_loader, bag_index=1)
    view.battle_system = MagicMock(is_trainer=False)
    view._throw_pokeball = MagicMock()

    view._on_interact()

    view._throw_pokeball.assert_called_once_with(view.battle_system)


def test_interact_pokeball_tab_in_trainer_battle_does_nothing(data_loader):
    view = make_view(data_loader, bag_index=1)
    view.battle_system = MagicMock(is_trainer=True)
    view._throw_pokeball = MagicMock()

    view._on_interact()

    view._throw_pokeball.assert_not_called()


def test_interact_pokeball_tab_outside_battle_does_nothing(data_loader):
    view = make_view(data_loader, bag_index=1)
    view.battle_system = None
    view._throw_pokeball = MagicMock()

    view._on_interact()

    view._throw_pokeball.assert_not_called()


def test_throw_pokeball_full_party_shows_message_on_battle_view(
    data_loader, monkeypatch
):
    monkeypatch.setattr(bag_view_module, "BattleView", MagicMock)
    view = make_view(data_loader, inventory=potions(1))
    battle_system = MagicMock()
    battle_system.player_manager.player.pokemon = [MagicMock() for _ in range(6)]
    view.previous_view = MagicMock()  # BattleView is now the MagicMock class

    view._throw_pokeball(battle_system)

    view.previous_view.show_messages.assert_called_once()
    battle_system.attempt_catch.assert_not_called()


def test_throw_pokeball_full_party_outside_battle_view_no_message(data_loader):
    view = make_view(data_loader, inventory=potions(1))
    battle_system = MagicMock()
    battle_system.player_manager.player.pokemon = [MagicMock() for _ in range(6)]
    view.previous_view = MagicMock()  # not a BattleView instance

    view._throw_pokeball(battle_system)

    view.window.show_view.assert_called_once_with(view.previous_view)


def test_throw_pokeball_success_attempts_catch(data_loader, monkeypatch):
    monkeypatch.setattr(bag_view_module, "BattleView", MagicMock)
    view = make_view(data_loader, inventory=potions(1))
    view.bagSystem.use_pokeball.return_value = "pokeball_item"
    battle_system = MagicMock()
    battle_system.player_manager.player.pokemon = [MagicMock()]
    battle_system.attempt_catch.return_value = {"caught": True, "messages": []}
    view.previous_view = MagicMock()  # BattleView is now the MagicMock class

    view._throw_pokeball(battle_system)

    battle_system.attempt_catch.assert_called_once_with("pokeball_item")
    view.previous_view.start_catch_attempt.assert_called_once_with(
        {"caught": True, "messages": []}
    )


def test_throw_pokeball_no_pokeball_available_does_not_attempt_catch(data_loader):
    view = make_view(data_loader, inventory=potions(1))
    view.bagSystem.use_pokeball.return_value = None
    battle_system = MagicMock()
    battle_system.player_manager.player.pokemon = [MagicMock()]

    view._throw_pokeball(battle_system)

    battle_system.attempt_catch.assert_not_called()


def test_change_bag_resets_current_index(data_loader):
    view = make_view(data_loader, inventory=potions(3))
    view.currentIndex = 2
    view.bagIndex = 0
    view.bag = {ItemCategory.MEDICINE: potions(3)}

    view.change_bag()

    assert view.currentIndex == 0
