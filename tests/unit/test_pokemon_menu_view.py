"""Tests for PokemonMenuView's item-use branch.

`__init__` needs an arcade window and a parsed .tmx layout, so these construct via
`__new__` and set only what `_use_item` reads — the same pattern as
tests/unit/test_battle_view.py.
"""

from typing import cast
from unittest.mock import MagicMock

import pytest

from src.states.pokemon_menu_view import PokemonMenuView


def _base_view(use_item_result: bool) -> PokemonMenuView:
    """A view wired for _use_item only. `use_item_result` is what the bag reports:
    False means the item was rejected (full HP, wrong status, full PP) and was
    NOT consumed."""
    view = PokemonMenuView.__new__(PokemonMenuView)

    view.bag = MagicMock()
    cast(MagicMock, view.bag).use_item.return_value = use_item_result
    view.item = "potion"
    view.window = MagicMock()
    view.system = MagicMock()
    mon = MagicMock()
    mon.name = "mudkip"
    view.system.team = [mon]
    view.system.team_index = 0
    return view


def make_battle_view(use_item_result: bool, monkeypatch):
    """Battle branch: previous_view is a BagView whose previous_view is a
    BattleView. Both classes are monkeypatched to the mock type so the
    isinstance() guards in _use_item pass."""
    view = _base_view(use_item_result)
    battle_view = MagicMock()
    bag_view = MagicMock()
    bag_view.previous_view = battle_view
    view.previous_view = bag_view
    view.battle_system = MagicMock()

    monkeypatch.setattr("src.states.pokemon_menu_view.BagView", MagicMock)
    monkeypatch.setattr("src.states.pokemon_menu_view.BattleView", MagicMock)
    return view, battle_view


def make_overworld_view(use_item_result: bool, monkeypatch):
    view = _base_view(use_item_result)
    view.previous_view = MagicMock()
    view.battle_system = None
    monkeypatch.setattr("src.states.pokemon_menu_view.BagView", MagicMock)
    return view


# --- bundled fix A: a rejected item must not cost a battle turn --------------


def test_rejected_item_does_not_consume_a_battle_turn(monkeypatch):
    """use_item returning False means nothing happened and no item was spent —
    running the turn anyway burns it and prints 'X used potion!'."""
    view, battle_view = make_battle_view(False, monkeypatch)

    view._use_item()

    battle_view.on_item_used.assert_not_called()


def test_accepted_item_does_consume_a_battle_turn(monkeypatch):
    view, battle_view = make_battle_view(True, monkeypatch)

    view._use_item()

    battle_view.on_item_used.assert_called_once()


def test_rejected_item_outside_battle_does_not_navigate(monkeypatch):
    """Overworld branch: a rejected item should not close the menu either."""
    view = make_overworld_view(False, monkeypatch)

    view._use_item()

    cast(MagicMock, view.window).show_view.assert_not_called()


def test_accepted_item_outside_battle_navigates_back(monkeypatch):
    view = make_overworld_view(True, monkeypatch)

    view._use_item()

    cast(MagicMock, view.window).show_view.assert_called_once()


# --- bundled fix B: the battle system must learn which mon was targeted ------


def test_battle_item_use_passes_the_target_pokemon(monkeypatch):
    view, battle_view = make_battle_view(True, monkeypatch)

    view._use_item()

    battle_view.on_item_used.assert_called_once_with("potion", "mudkip")


def test_use_item_without_a_bag_raises():
    view = PokemonMenuView.__new__(PokemonMenuView)
    view.bag = None
    with pytest.raises(RuntimeError):
        view._use_item()
