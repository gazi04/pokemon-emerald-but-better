"""Tests for PlayerInput: keyboard state -> movement/interact intents.

Uses the real ControlsConfig so key names resolve to real arcade.key.* ints.
`arcade.get_sprites_at_point` is monkeypatched per-test since it needs a real
sprite list otherwise.
"""

from unittest.mock import MagicMock

import arcade

from data.config import ControlsConfig
from src.controllers.player_input import PlayerInput
from src.core.event_bus import global_bus
from src.core.events import NpcInteractEvent
from src.model.motion.player_motion import PlayerMotion

CONTROLS = ControlsConfig()


def make_state(px=0.0, py=0.0, direction="down", moving=False):
    state = PlayerMotion(
        pixel_x=px, pixel_y=py, grid_x=0, grid_y=0, map_name="littleroot_town"
    )
    state.direction = direction
    state.moving = moving
    return state


def test_moving_state_short_circuits_to_none():
    controller = PlayerInput()
    state = make_state(moving=True)

    result = controller.process_input(
        state, {arcade.key.UP}, CONTROLS, MagicMock(), MagicMock()
    )

    assert result is None


def test_no_keys_pressed_returns_none(monkeypatch):
    monkeypatch.setattr(
        "src.controllers.player_input.arcade.get_sprites_at_point", lambda *a: []
    )
    controller = PlayerInput()
    state = make_state()

    result = controller.process_input(state, set(), CONTROLS, MagicMock(), MagicMock())

    assert result is None


def test_interact_press_edge_publishes_npc_interact(monkeypatch):
    """Only fires once the frame the key transitions from up to down."""
    monkeypatch.setattr(
        "src.controllers.player_input.arcade.get_sprites_at_point",
        lambda point, npcs: [SimpleTarget("rival_1")],
    )
    controller = PlayerInput()
    state = make_state(direction="up")
    events = []
    global_bus.subscribe(NpcInteractEvent, events.append)

    result = controller.process_input(
        state, {arcade.key.Z}, CONTROLS, MagicMock(), MagicMock(), npcs=MagicMock()
    )

    assert result is None
    assert len(events) == 1
    assert events[0].npc_id == "rival_1"


def test_interact_held_across_frames_does_not_refire(monkeypatch):
    monkeypatch.setattr(
        "src.controllers.player_input.arcade.get_sprites_at_point",
        lambda point, npcs: [SimpleTarget("rival_1")],
    )
    controller = PlayerInput()
    state = make_state(direction="up")
    events = []
    global_bus.subscribe(NpcInteractEvent, events.append)

    controller.process_input(
        state, {arcade.key.Z}, CONTROLS, MagicMock(), MagicMock(), npcs=MagicMock()
    )
    controller.process_input(
        state, {arcade.key.Z}, CONTROLS, MagicMock(), MagicMock(), npcs=MagicMock()
    )

    assert len(events) == 1


def test_direction_press_hits_transition(monkeypatch):
    monkeypatch.setattr(
        "src.controllers.player_input.arcade.get_sprites_at_point", lambda *a: []
    )
    controller = PlayerInput()
    state = make_state()
    transitions = MagicMock()
    transitions.find.return_value = {"target_map": "oldale_town"}

    result = controller.process_input(
        state, {arcade.key.UP}, CONTROLS, MagicMock(), transitions
    )

    assert result == {"type": "transition", "properties": {"target_map": "oldale_town"}}


def test_direction_press_blocked_by_npc_on_target_tile(monkeypatch):
    calls = []

    def fake_hit(point, sprite_list):
        calls.append(sprite_list)
        return [SimpleTarget("blocker")] if sprite_list == "npcs" else []

    monkeypatch.setattr(
        "src.controllers.player_input.arcade.get_sprites_at_point", fake_hit
    )
    controller = PlayerInput()
    state = make_state()
    transitions = MagicMock()
    transitions.find.return_value = None

    result = controller.process_input(
        state, {arcade.key.UP}, CONTROLS, "collisions", transitions, npcs="npcs"
    )

    assert result == {"type": "turn", "direction": "up"}


def test_direction_press_blocked_by_collision(monkeypatch):
    def fake_hit(point, sprite_list):
        return [SimpleTarget("wall")] if sprite_list == "collisions" else []

    monkeypatch.setattr(
        "src.controllers.player_input.arcade.get_sprites_at_point", fake_hit
    )
    controller = PlayerInput()
    state = make_state()
    transitions = MagicMock()
    transitions.find.return_value = None

    result = controller.process_input(
        state, {arcade.key.UP}, CONTROLS, "collisions", transitions
    )

    assert result == {"type": "turn", "direction": "up"}


def test_direction_press_free_move(monkeypatch):
    monkeypatch.setattr(
        "src.controllers.player_input.arcade.get_sprites_at_point", lambda *a: []
    )
    controller = PlayerInput()
    state = make_state(px=0.0, py=0.0)
    transitions = MagicMock()
    transitions.find.return_value = None

    result = controller.process_input(
        state, {arcade.key.UP}, CONTROLS, MagicMock(), transitions
    )

    assert result is not None
    assert result["type"] == "move"
    assert state.direction == "up"


class SimpleTarget:
    def __init__(self, npc_id):
        self.npc_id = npc_id
