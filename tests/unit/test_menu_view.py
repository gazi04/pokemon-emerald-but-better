"""Tests for MenuView: save feedback timer, cursor wrap, action dispatch.

`__init__` needs a real overworld view + parsed .tmx UI layout, so these
construct via `__new__` and set only what each method reads — same pattern
as tests/unit/test_battle_view.py.
"""

from typing import Any
from unittest.mock import MagicMock

import arcade

from src.core.event_bus import global_bus
from src.core.events import CloseViewEvent, SaveCompletedEvent, SaveGameRequestEvent
from src.states.menu_view import MenuView


def make_view(num_buttons=4) -> Any:
    view: Any = MenuView.__new__(MenuView)
    view.overworld = MagicMock()
    view.ui = MagicMock()
    view.ui.buttons = [MagicMock() for _ in range(num_buttons)]
    view.selectedIndex = 0
    view._save_feedback = ""
    view._save_feedback_timer = 0.0
    return view


def test_on_save_completed_success_sets_feedback_and_timer():
    view = make_view()

    view._on_save_completed(SaveCompletedEvent(success=True))

    assert view._save_feedback == "Game saved!"
    assert view._save_feedback_timer == 2.0


def test_on_save_completed_failure_sets_feedback():
    view = make_view()

    view._on_save_completed(SaveCompletedEvent(success=False))

    assert view._save_feedback == "Save failed!"


def test_on_update_counts_timer_down():
    view = make_view()
    view._save_feedback = "Game saved!"
    view._save_feedback_timer = 2.0

    view.on_update(0.5)

    assert view._save_feedback_timer == 1.5
    assert view._save_feedback == "Game saved!"


def test_on_update_clears_feedback_when_timer_expires():
    view = make_view()
    view._save_feedback = "Game saved!"
    view._save_feedback_timer = 0.2

    view.on_update(1.0)

    assert view._save_feedback_timer <= 0
    assert view._save_feedback == ""


def test_on_update_noop_when_timer_already_zero():
    view = make_view()

    view.on_update(1.0)

    assert view._save_feedback_timer == 0.0


def test_up_wraps_from_zero_to_last_index():
    view = make_view(num_buttons=4)

    view.on_key_press(arcade.key.UP, 0)

    assert view.selectedIndex == 3
    view.ui.set_y_of_cursor.assert_called_once_with(3)


def test_down_wraps_from_last_to_zero():
    view = make_view(num_buttons=4)
    view.selectedIndex = 3

    view.on_key_press(arcade.key.DOWN, 0)

    assert view.selectedIndex == 0
    view.ui.set_y_of_cursor.assert_called_once_with(0)


def test_down_advances_without_wrap():
    view = make_view(num_buttons=4)

    view.on_key_press(arcade.key.DOWN, 0)

    assert view.selectedIndex == 1


def test_cancel_publishes_close_view_event():
    view = make_view()
    events = []
    global_bus.subscribe(CloseViewEvent, events.append)

    view.on_key_press(arcade.key.X, 0)

    assert len(events) == 1


def test_action_index_0_overlays_pokedex():
    view = make_view()
    view.selectedIndex = 0
    view.overlay = MagicMock()

    view.action()

    view.overlay.assert_called_once_with("pokedex", previous_view=view)


def test_action_index_1_overlays_pokemon_menu():
    view = make_view()
    view.selectedIndex = 1
    view.overlay = MagicMock()

    view.action()

    view.overlay.assert_called_once_with("pokemon_menu", previous_view=view)


def test_action_index_2_overlays_bag():
    view = make_view()
    view.selectedIndex = 2
    view.overlay = MagicMock()

    view.action()

    view.overlay.assert_called_once_with("bag", previous_view=view)


def test_action_index_3_publishes_save_request():
    view = make_view()
    view.selectedIndex = 3
    events = []
    global_bus.subscribe(SaveGameRequestEvent, events.append)

    view.action()

    assert len(events) == 1
