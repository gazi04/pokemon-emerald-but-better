"""Tests for BattleView's enemy-swap chokepoint.

`BattleView.__init__` needs a real arcade window and a parsed .tmx layout, but
`set_enemy` only touches five attributes. Constructing via `__new__` skips
`__init__` entirely, so the swap logic is testable without a GL context.
"""

from types import SimpleNamespace

import arcade

from data.config import CONFIG
from unittest.mock import MagicMock

import pytest

from src.enums.battle_state import BattleState
from src.model.battle.battle_pokemon import BattlePokemon
from src.model.static.trainer import TrainerPokemonMove
from src.states.battle_view import BattleView

# poochyena/zigzagoon declare abilities the fixture ability.json doesn't carry,
# and set_enemy takes the ability as a parameter anyway — so use one that exists.
FIXTURE_ABILITY = "intimidate"
MOVES = [TrainerPokemonMove("tackle", 25)]


@pytest.fixture
def battle_view(data_loader, player_manager):
    """A BattleView with only what set_enemy reads. No arcade window."""
    view = BattleView.__new__(BattleView)
    view.data_loader = data_loader
    view.player_manager = player_manager
    view.enemy_sprite = MagicMock()
    view.battle_system = MagicMock()
    return view


def test_set_enemy_marks_the_new_pokemon_as_seen(battle_view, player_manager):
    """B1: a trainer's 2nd+ Pokémon must reach the Pokédex. Before the fix
    mark_seen only ever fired once, in __init__, for the lead."""
    assert player_manager.get_seen_pokemon() == []

    battle_view.set_enemy("poochyena", 5, MOVES, FIXTURE_ABILITY)

    assert player_manager.get_seen_pokemon() == ["poochyena"]


def test_set_enemy_marks_each_successive_switch_in(battle_view, player_manager):
    battle_view.set_enemy("poochyena", 5, MOVES, FIXTURE_ABILITY)
    battle_view.set_enemy("zigzagoon", 7, MOVES, FIXTURE_ABILITY)

    assert player_manager.get_seen_pokemon() == ["poochyena", "zigzagoon"]


def test_set_enemy_rejects_unknown_species(battle_view):
    """set_enemy takes a lowercase DataLoader id by contract — require_pokemon
    is case-sensitive, so bad casing fails loudly here rather than silently
    writing a broken Pokédex entry. Lowercase normalization for the seen list
    itself is PlayerSave.mark_seen's job."""
    with pytest.raises(KeyError):
        battle_view.set_enemy("POOCHYENA", 5, MOVES, FIXTURE_ABILITY)


def test_set_enemy_rebinds_the_battle_system_enemy(battle_view):
    """The desync the docstring warns about: view and system must agree on who
    is on the field."""
    battle_view.set_enemy("poochyena", 5, MOVES, FIXTURE_ABILITY)

    assert isinstance(battle_view.enemy_battle, BattlePokemon)
    assert battle_view.battle_system.enemy_pokemon is battle_view.enemy_battle
    assert battle_view.enemy_battle.level == 5


def test_set_enemy_retextures_the_sprite(battle_view, data_loader):
    battle_view.set_enemy("poochyena", 5, MOVES, FIXTURE_ABILITY)

    expected = data_loader.require_pokemon("poochyena").sprites.front
    battle_view.enemy_sprite.set_new_texture.assert_called_once_with(expected)


# ---------------------------------------------------------------------------
# Battle-state dispatcher (what_happend_after_text) and other turn logic.
# `wired_view` mocks every collaborator + sub-method so each test isolates a
# single branch instead of exercising the whole turn machinery.
# ---------------------------------------------------------------------------


@pytest.fixture
def wired_view(data_loader, player_manager):
    view = BattleView.__new__(BattleView)
    view.data_loader = data_loader
    view.player_manager = player_manager
    view.battle_system = MagicMock()
    view.ui = MagicMock()
    view.your_battle = MagicMock()
    view.your_battle.name = "mudkip"
    view.your_battle.level = 10
    view.your_battle.moves = [MagicMock(pp=10)]
    view.your_battle.moves[0].name = "tackle"
    view.overworld_view = MagicMock()
    view.enemy_sprite = MagicMock()
    view.your_sprite = MagicMock()
    view.is_trainer = False
    view.trainer_data = None
    view.prize_money = 0
    view.npc_id = None
    view._pending_catch_close = False
    view.learning_move_mode = False
    view._on_learning_done = None
    view.run = MagicMock()
    view.overlay = MagicMock()
    view.close = MagicMock()
    view.swap = MagicMock()
    view._on_continue_turn = MagicMock()
    view._ending_turn = MagicMock()
    view._trainer_give_exp = MagicMock()
    view._trainer_send_next_pokemon = MagicMock()
    view._handle_player_fainted = MagicMock()
    view._end_loss = MagicMock()
    view._continue_move_learning = MagicMock()
    view._handle_battle_finishing = MagicMock()
    view._refresh_active_pokemon_ui = MagicMock()
    return view


def test_pending_catch_close_runs_and_clears_flag(wired_view):
    wired_view._pending_catch_close = True

    wired_view.what_happend_after_text()

    wired_view.run.assert_called_once()
    assert wired_view._pending_catch_close is False


def test_caught_state_with_messages_queues_them_and_defers_close(wired_view):
    wired_view.battle_system.battle_state = BattleState.CAUGHT
    wired_view.battle_system.add_caught_pokemon.return_value = {"messages": ["Gotcha!"]}

    wired_view.what_happend_after_text()

    wired_view.ui.queue_messages.assert_called_once_with(["Gotcha!"])
    wired_view.ui.switch_mode.assert_called_once_with("dialog")
    assert wired_view._pending_catch_close is True
    wired_view.run.assert_not_called()


def test_caught_state_without_messages_runs_immediately(wired_view):
    wired_view.battle_system.battle_state = BattleState.CAUGHT
    wired_view.battle_system.add_caught_pokemon.return_value = {"messages": []}

    wired_view.what_happend_after_text()

    wired_view.run.assert_called_once()


def test_currently_turn_dispatches_to_continue_turn(wired_view):
    wired_view.battle_system.battle_state = BattleState.CURRENTLY_TURN

    wired_view.what_happend_after_text()

    wired_view._on_continue_turn.assert_called_once()


@pytest.mark.parametrize(
    "state", [BattleState.INTRO, BattleState.POST_TURN, BattleState.WAITING]
)
def test_intro_post_turn_waiting_dispatch_to_ending_turn(wired_view, state):
    wired_view.battle_system.battle_state = state

    wired_view.what_happend_after_text()

    wired_view._ending_turn.assert_called_once()


def test_switching_state_queues_switch_turn_messages(wired_view):
    wired_view.battle_system.battle_state = BattleState.SWITCHING
    wired_view.battle_system.switch_turn.return_value = ["Go, mudkip!"]

    wired_view.what_happend_after_text()

    wired_view.ui.queue_messages.assert_called_once_with(["Go, mudkip!"])
    wired_view.ui.switch_mode.assert_called_once_with("dialog")


def test_trainer_switch_dispatches_to_give_exp(wired_view):
    wired_view.battle_system.battle_state = BattleState.TRAINER_SWITCH

    wired_view.what_happend_after_text()

    wired_view._trainer_give_exp.assert_called_once()


def test_trainer_sending_dispatches_to_send_next_pokemon(wired_view):
    wired_view.battle_system.battle_state = BattleState.TRAINER_SENDING

    wired_view.what_happend_after_text()

    wired_view._trainer_send_next_pokemon.assert_called_once()


def test_player_fainted_dispatches_to_handler(wired_view):
    wired_view.battle_system.battle_state = BattleState.PLAYER_FAINTED

    wired_view.what_happend_after_text()

    wired_view._handle_player_fainted.assert_called_once()


def test_lost_dispatches_to_end_loss(wired_view):
    wired_view.battle_system.battle_state = BattleState.LOST

    wired_view.what_happend_after_text()

    wired_view._end_loss.assert_called_once()


def test_learning_move_dispatches_to_continue_move_learning(wired_view):
    wired_view.battle_system.battle_state = BattleState.LEARNING_MOVE

    wired_view.what_happend_after_text()

    wired_view._continue_move_learning.assert_called_once()


def test_end_dispatches_to_handle_battle_finishing(wired_view):
    wired_view.battle_system.battle_state = BattleState.END

    wired_view.what_happend_after_text()

    wired_view._handle_battle_finishing.assert_called_once()


def test_start_turn_queues_turn_messages_and_switches_to_dialog(wired_view):
    wired_view.battle_system.turn.return_value = ["mudkip used tackle!"]

    wired_view.start_turn(0)

    wired_view.battle_system.turn.assert_called_once_with(0)
    wired_view.ui.queue_messages.assert_called_once_with(["mudkip used tackle!"])
    wired_view.ui.switch_mode.assert_called_once_with("dialog")


def test_on_item_used_forwards_item_and_target(wired_view):
    wired_view.battle_system.turn_use_item.return_value = ["Used potion!"]

    wired_view.on_item_used("potion", "mudkip")

    wired_view.battle_system.turn_use_item.assert_called_once_with("potion", "mudkip")
    wired_view.ui.queue_messages.assert_called_once_with(["Used potion!"])


def test_switch_turn_sets_switching_state_and_refreshes_ui(wired_view):
    wired_view.battle_system.switch_pokemon.return_value = ["Come back!"]

    wired_view.switch_turn()

    assert wired_view.battle_system.battle_state == BattleState.SWITCHING
    wired_view.ui.queue_messages.assert_called_once_with(["Come back!"])
    wired_view._refresh_active_pokemon_ui.assert_called_once()


def test_force_switch_returns_to_waiting_state(wired_view):
    wired_view.battle_system.complete_forced_switch.return_value = ["Go, treecko!"]

    wired_view.force_switch()

    wired_view.ui.queue_messages.assert_called_once_with(["Go, treecko!"])
    assert wired_view.battle_system.battle_state == BattleState.WAITING
    wired_view._refresh_active_pokemon_ui.assert_called_once()


def test_handle_player_fainted_offers_switch_when_usable_pokemon_remain(wired_view):
    wired_view.battle_system.has_usable_pokemon.return_value = True
    wired_view._handle_player_fainted = BattleView._handle_player_fainted.__get__(
        wired_view
    )
    wired_view._handle_player_loss = MagicMock()

    wired_view._handle_player_fainted()

    wired_view.overlay.assert_called_once_with(
        "pokemon_menu",
        previous_view=wired_view,
        battle_system=wired_view.battle_system,
        forced_switch=True,
    )
    wired_view._handle_player_loss.assert_not_called()


def test_handle_player_fainted_ends_the_game_with_no_usable_pokemon(wired_view):
    wired_view.battle_system.has_usable_pokemon.return_value = False
    wired_view._handle_player_fainted = BattleView._handle_player_fainted.__get__(
        wired_view
    )
    wired_view._handle_player_loss = MagicMock()

    wired_view._handle_player_fainted()

    wired_view._handle_player_loss.assert_called_once()
    wired_view.overlay.assert_not_called()


def test_active_menu_size_main_panel(wired_view):
    wired_view.ui.active_component = "main"
    wired_view.ui.menu_panel.main_buttons = [MagicMock()] * 4

    assert wired_view._active_menu_size() == 4


def test_active_menu_size_moves_panel_counts_moves(wired_view):
    wired_view.ui.active_component = "moves"
    wired_view.your_battle.moves = [MagicMock(), MagicMock()]

    assert wired_view._active_menu_size() == 2


def test_active_menu_size_none_when_no_menu_active(wired_view):
    wired_view.ui.active_component = "dialog"

    assert wired_view._active_menu_size() is None


def test_move_menu_cursor_guarded_noop_with_two_buttons(wired_view):
    wired_view.ui.active_component = "main"
    wired_view.ui.menu_panel.selection_index = 0

    wired_view._move_menu_cursor(-2, num_buttons=2, guarded=True)

    assert wired_view.ui.menu_panel.selection_index == 0


def test_move_menu_cursor_wraps_with_modulo(wired_view):
    wired_view.ui.active_component = "main"
    wired_view.ui.menu_panel.selection_index = 0

    wired_view._move_menu_cursor(-2, num_buttons=4, guarded=True)

    assert wired_view.ui.menu_panel.selection_index == 2


def test_move_menu_cursor_left_right_always_move_even_when_guarded_would_block(
    wired_view,
):
    wired_view.ui.active_component = "main"
    wired_view.ui.menu_panel.selection_index = 0

    wired_view._move_menu_cursor(-1, num_buttons=2, guarded=False)

    assert wired_view.ui.menu_panel.selection_index == 1


def test_move_menu_cursor_on_moves_panel_calls_move_hover(wired_view):
    wired_view.ui.active_component = "moves"
    wired_view.ui.menu_panel.selection_index = 0
    wired_view.your_battle.moves = [MagicMock(pp=10), MagicMock(pp=10)]
    wired_view.your_battle.moves[0].name = "tackle"
    wired_view.your_battle.moves[1].name = "growl"
    wired_view.move_hover = MagicMock()

    wired_view._move_menu_cursor(1, num_buttons=2, guarded=False)

    assert wired_view.ui.menu_panel.selection_index == 1
    wired_view.move_hover.assert_called_once_with(1)


def test_handle_main_menu_select_index0_opens_moves(wired_view):
    wired_view.ui.menu_panel.selection_index = 0

    wired_view._handle_main_menu_select()

    wired_view.ui.switch_mode.assert_called_once_with("moves")


def test_handle_main_menu_select_index1_overlays_bag(wired_view):
    wired_view.ui.menu_panel.selection_index = 1

    wired_view._handle_main_menu_select()

    wired_view.overlay.assert_called_once_with(
        "bag", previous_view=wired_view, battle_system=wired_view.battle_system
    )


def test_handle_main_menu_select_index2_overlays_pokemon_menu(wired_view):
    wired_view.ui.menu_panel.selection_index = 2

    wired_view._handle_main_menu_select()

    wired_view.overlay.assert_called_once_with(
        "pokemon_menu", previous_view=wired_view, battle_system=wired_view.battle_system
    )


def test_handle_main_menu_select_index3_attempts_run(wired_view):
    wired_view.ui.menu_panel.selection_index = 3
    wired_view._attempt_run = MagicMock()

    wired_view._handle_main_menu_select()

    wired_view._attempt_run.assert_called_once()


def test_trainer_send_next_pokemon_defeated_message_when_none_left(wired_view):
    wired_view.battle_system.next_trainer_pokemon = None
    wired_view.prize_money = 150
    wired_view._trainer_send_next_pokemon = (
        BattleView._trainer_send_next_pokemon.__get__(wired_view)
    )

    wired_view._trainer_send_next_pokemon()

    wired_view.ui.queue_messages.assert_called_once_with(
        ["Trainer was defeated!!!", "You got $150!"]
    )
    assert wired_view.battle_system.battle_state == BattleState.END


def test_trainer_send_next_pokemon_sends_the_next_one(wired_view, data_loader):
    next_data = SimpleNamespace(
        name="poochyena", level=8, moves=MOVES, ability=FIXTURE_ABILITY
    )
    wired_view.battle_system.next_trainer_pokemon = next_data
    wired_view.data_loader = data_loader
    wired_view.player_manager.mark_seen = MagicMock()
    wired_view._trainer_send_next_pokemon = (
        BattleView._trainer_send_next_pokemon.__get__(wired_view)
    )

    wired_view._trainer_send_next_pokemon()

    assert wired_view.enemy_battle.level == 8
    wired_view.ui.set_enemy_info.assert_called_once_with("POOCHYENA", 8)
    assert wired_view.battle_system.battle_state == BattleState.WAITING


# --- empty moveset ----------------------------------------------------------
# A moveless pokemon reaching the move menu used to divide by zero in
# _move_menu_cursor (`% num_buttons`) and IndexError in _refresh_active_pokemon_ui
# (`moves[0]`). wild_moveset.py guarantees wilds have at least Tackle, so this
# needs a hand-edited save today — but both guards are one data change from
# mattering, and neither had a test.


def _menu_view(moves, component="moves"):
    """A BattleView with only what _active_menu_size/on_key_press read.
    MagicMock rather than SimpleNamespace so pyright accepts the assignments to
    BattleView's typed attributes, matching the battle_view fixture above."""
    view = BattleView.__new__(BattleView)
    view.your_battle = MagicMock()
    view.your_battle.moves = moves
    view.ui = MagicMock()
    view.ui.active_component = component
    view.ui.menu_panel.main_buttons = []
    view.ui.menu_panel.selection_index = 0
    return view


def test_empty_moveset_reports_no_active_menu():
    """None is the existing 'ignore key presses' sentinel, so an empty move
    menu behaves like no menu instead of crashing the cursor."""
    assert _menu_view([])._active_menu_size() is None


def test_populated_moveset_reports_its_size():
    view = _menu_view([object(), object()])

    assert view._active_menu_size() == 2


def test_empty_main_menu_reports_no_active_menu():
    view = _menu_view([], component="main")

    assert view._active_menu_size() is None


def test_key_press_on_an_empty_move_menu_does_not_raise():
    """The regression proper: on_key_press bails on None before reaching the
    modulo that would divide by zero.

    Left/right specifically — up/down pass `guarded=True`, and the
    `num_buttons <= 2` guard happens to skip the modulo, so they cannot prove
    the fix. Left/right reach `% num_buttons` unconditionally.
    """
    view = _menu_view([])
    view.is_pressed = lambda config_key, symbol: config_key == CONFIG.controls.left

    view.on_key_press(arcade.key.LEFT, 0)

    assert view.ui.menu_panel.selection_index == 0
