"""Tests for PokemonMenuView's item-use branch.

`__init__` needs an arcade window and a parsed .tmx layout, so these construct via
`__new__` and set only what `_use_item` reads — the same pattern as
tests/unit/test_battle_view.py.
"""

from typing import Any, cast
from unittest.mock import MagicMock

import arcade
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


# --- _do_forced_switch -------------------------------------------------------


def make_forced_switch_view(hp=20, team_index=1, monkeypatch=None) -> Any:
    view: Any = PokemonMenuView.__new__(PokemonMenuView)
    view.system = MagicMock()
    selected = MagicMock(hp=hp)
    team = [MagicMock(hp=20), MagicMock(hp=20)]
    team[team_index] = selected
    view.system.team = team
    view.system.team_index = team_index
    view.ui = MagicMock()
    view.window = MagicMock()
    view.previous_view = MagicMock()
    if monkeypatch is not None:
        monkeypatch.setattr("src.states.pokemon_menu_view.BattleView", MagicMock)
    return view


def test_forced_switch_rejects_fainted_pokemon():
    view = make_forced_switch_view(hp=0, team_index=1)

    view._do_forced_switch()

    view.system.confirm_switch.assert_not_called()


def test_forced_switch_rejects_the_already_active_pokemon():
    view = make_forced_switch_view(hp=20, team_index=0)

    view._do_forced_switch()

    view.system.confirm_switch.assert_not_called()


def test_forced_switch_confirms_and_returns_to_battle_view(monkeypatch):
    view = make_forced_switch_view(hp=20, team_index=1, monkeypatch=monkeypatch)
    battle_view = view.previous_view = MagicMock()

    view._do_forced_switch()

    view.system.confirm_switch.assert_called_once_with(1)
    battle_view.force_switch.assert_called_once()
    view.window.show_view.assert_called_once_with(battle_view)


def test_forced_switch_outside_battle_skips_force_switch_call():
    view = make_forced_switch_view(hp=20, team_index=1)
    view.previous_view = MagicMock()  # not a BattleView instance

    view._do_forced_switch()

    view.system.confirm_switch.assert_called_once_with(1)
    view.window.show_view.assert_called_once_with(view.previous_view)


# --- _tooltip_action ----------------------------------------------------------


def make_tooltip_view(bag, battle_system=None, monkeypatch=None) -> Any:
    view: Any = PokemonMenuView.__new__(PokemonMenuView)
    view.bag = bag
    view.item = "potion"
    view.battle_system = battle_system
    view.system = MagicMock()
    mon = MagicMock()
    mon.name = "mudkip"
    view.system.team = [mon]
    view.system.team_index = 0
    view.system.tooltip_index = 0
    view.ui = MagicMock()
    view.window = MagicMock()
    view.previous_view = MagicMock()
    view.overlay = MagicMock()
    view._use_item = MagicMock()
    view._move_pokemon = MagicMock()
    return view


# X2: "Give it" used to assign held_item directly, bypassing
# BagSystem.give_held_item entirely — so nothing checked `holdable`, the item
# was never consumed (unlimited duplication), and an already-held item was
# silently overwritten and lost. The old version of this test asserted that
# direct write against a MagicMock bag, which is to say it pinned the bug.


def test_tooltip_index2_delegates_to_the_bag():
    view = make_tooltip_view(bag=MagicMock())
    view.bag.give_held_item.return_value = True
    view.system.tooltip_index = 2

    view._tooltip_action()

    view.bag.give_held_item.assert_called_once_with("potion", "mudkip")


def test_tooltip_index2_never_writes_held_item_directly():
    """The bag owns the mutation. A direct write skips the holdable check and
    the bag decrement — the duplication exploit."""
    view = make_tooltip_view(bag=MagicMock())
    view.bag.give_held_item.return_value = False
    view._get_current_pokemon().held_item = None
    view.system.tooltip_index = 2

    view._tooltip_action()

    assert view._get_current_pokemon().held_item is None


def test_tooltip_index2_returns_to_the_bag_when_the_item_was_given():
    view = make_tooltip_view(bag=MagicMock())
    view.bag.give_held_item.return_value = True
    view.system.tooltip_index = 2

    view._tooltip_action()

    view.window.show_view.assert_called_once_with(view.previous_view)


def test_tooltip_index2_stays_put_when_the_item_was_refused():
    """Refused (not holdable, or already holding something) — mirrors how
    _use_item already treats a rejected item."""
    view = make_tooltip_view(bag=MagicMock())
    view.bag.give_held_item.return_value = False
    view.system.tooltip_index = 2

    view._tooltip_action()

    view.window.show_view.assert_not_called()


def test_tooltip_index2_without_bag_does_nothing():
    view = make_tooltip_view(bag=None)
    view.system.tooltip_index = 2

    view._tooltip_action()

    view.window.show_view.assert_not_called()


def test_tooltip_index1_with_pp_item_opens_move_picker():
    bag = MagicMock()
    bag.is_pp_item.return_value = True
    view = make_tooltip_view(bag=bag)
    view.system.tooltip_index = 1

    view._tooltip_action()

    view.overlay.assert_called_once()
    assert view.overlay.call_args.args[0] == "pokemon_information"
    assert view.overlay.call_args.kwargs["select_move"] is True
    view._use_item.assert_not_called()


def test_tooltip_index1_with_non_pp_item_uses_it_directly():
    bag = MagicMock()
    bag.is_pp_item.return_value = False
    view = make_tooltip_view(bag=bag)
    view.system.tooltip_index = 1

    view._tooltip_action()

    view._use_item.assert_called_once()
    view.overlay.assert_not_called()


def test_tooltip_index1_without_bag_and_multiple_pokemon_moves(monkeypatch):
    view = make_tooltip_view(bag=None)
    view.system.tooltip_index = 1
    view.system.team = [MagicMock(), MagicMock()]

    view._tooltip_action()

    view._move_pokemon.assert_called_once()


def test_tooltip_index1_without_bag_and_single_pokemon_does_nothing():
    view = make_tooltip_view(bag=None)
    view.system.tooltip_index = 1
    view.system.team = [MagicMock()]

    view._tooltip_action()

    view._move_pokemon.assert_not_called()


def test_tooltip_index0_always_opens_pokemon_information():
    view = make_tooltip_view(bag=None)
    view.system.tooltip_index = 0

    view._tooltip_action()

    view.overlay.assert_called_once_with(
        "pokemon_information",
        previous_view=view,
        pokemon=view._get_current_pokemon(),
    )


# --- _handle_menu_input -------------------------------------------------------


def make_menu_input_view() -> Any:
    view: Any = PokemonMenuView.__new__(PokemonMenuView)
    view.forced_switch = False
    view.system = MagicMock()
    view.system.is_moving_pokemon = False
    view.system.team_index = 0
    view.battle_system = None
    view.window = MagicMock()
    view.previous_view = MagicMock()
    view.ui = MagicMock()
    view._do_forced_switch = MagicMock()
    return view


def test_cancel_blocked_during_forced_switch():
    view = make_menu_input_view()
    view.forced_switch = True

    view._handle_menu_input(arcade.key.X)

    view.window.show_view.assert_not_called()


def test_cancel_while_moving_pokemon_cancels_the_move():
    view = make_menu_input_view()
    view.system.is_moving_pokemon = True

    view._handle_menu_input(arcade.key.X)

    view.system.cancel_moving.assert_called_once()
    view.window.show_view.assert_not_called()


def test_cancel_normally_returns_to_previous_view():
    view = make_menu_input_view()

    view._handle_menu_input(arcade.key.X)

    view.window.show_view.assert_called_once_with(view.previous_view)


def test_interact_during_forced_switch_calls_do_forced_switch():
    view = make_menu_input_view()
    view.forced_switch = True

    view._handle_menu_input(arcade.key.Z)

    view._do_forced_switch.assert_called_once()


def test_up_down_move_team_index():
    view = make_menu_input_view()

    view._handle_menu_input(arcade.key.DOWN)
    view.system.move_team_index.assert_called_once_with(1)

    view.system.move_team_index.reset_mock()
    view._handle_menu_input(arcade.key.UP)
    view.system.move_team_index.assert_called_once_with(-1)
