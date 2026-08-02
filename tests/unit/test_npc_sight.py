"""Trainer line-of-sight: spotting the player, walking over, and challenging."""

from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import arcade
import pytest

from src.constants import TILE_SIZE
from src.core.event_bus import global_bus
from src.core.events import NpcInteractEvent, NpcSpottedPlayerEvent
from src.systems.npc_behaviors import (
    IdleBehavior,
    TrainerSightBehavior,
    WanderBehavior,
    make_behavior,
)


class FakeWorld:
    """Stands in for NpcController: scripted sight distance + walkability."""

    def __init__(self, sight=None, walkable=True):
        self.sight = sight
        self.walkable = walkable
        self.walk_queries = []

    def line_of_sight(self, npc, max_tiles):
        return self.sight

    def can_walk(self, x, y, asking):
        self.walk_queries.append((x, y))
        return self.walkable


def make_npc(npc_id="trainer", direction="down", x=100.0, y=100.0):
    return SimpleNamespace(
        npc_id=npc_id,
        motion=SimpleNamespace(pixel_x=x, pixel_y=y, direction=direction, moving=False),
    )


@pytest.fixture
def captured():
    """Collect every spotted/interact event published during a test."""
    events = []
    spotted = lambda e: events.append(("spotted", e.npc_id))  # noqa: E731
    interact = lambda e: events.append(("interact", e.npc_id))  # noqa: E731
    global_bus.subscribe(NpcSpottedPlayerEvent, spotted)
    global_bus.subscribe(NpcInteractEvent, interact)
    yield events
    global_bus.unsubscribe(NpcSpottedPlayerEvent, spotted)
    global_bus.unsubscribe(NpcInteractEvent, interact)


# --- gating -----------------------------------------------------------------


def test_npc_without_team_never_challenges(captured):
    inner = IdleBehavior()
    behavior = TrainerSightBehavior(inner, can_challenge=lambda _id: False)
    world = FakeWorld(sight=2)  # player is right there...

    assert behavior.decide(make_npc(), world, 0.1) is None
    assert behavior.state == behavior.PATROL
    assert captured == []  # ...but no team, so nothing happens


def test_defeated_trainer_stops_challenging(captured):
    behavior = TrainerSightBehavior(IdleBehavior(), can_challenge=lambda _id: False)
    behavior.decide(make_npc(), FakeWorld(sight=1), 0.1)
    assert captured == []


def test_player_out_of_sight_runs_inner_behavior(captured):
    behavior = TrainerSightBehavior(IdleBehavior(), can_challenge=lambda _id: True)
    world = FakeWorld(sight=None)  # nothing in the line

    assert behavior.decide(make_npc(), world, 0.1) is None
    assert behavior.state == behavior.PATROL
    assert captured == []


# --- spotting and approaching ----------------------------------------------


def test_spotting_publishes_event_and_steps_toward_player(captured):
    behavior = TrainerSightBehavior(IdleBehavior(), can_challenge=lambda _id: True)
    world = FakeWorld(sight=3)
    npc = make_npc(direction="down", x=100.0, y=100.0)

    intent = behavior.decide(npc, world, 0.1)

    assert ("spotted", "trainer") in captured
    assert behavior.state == behavior.APPROACH
    assert intent is not None
    assert intent["type"] == "move"
    assert intent["direction"] == "down"
    assert intent["target_y"] == 100.0 - TILE_SIZE  # y-up: "down" decreases y


def test_adjacent_player_triggers_dialog_immediately(captured):
    behavior = TrainerSightBehavior(IdleBehavior(), can_challenge=lambda _id: True)
    world = FakeWorld(sight=1)  # already face to face

    intent = behavior.decide(make_npc(), world, 0.1)

    assert intent is None
    assert behavior.state == behavior.DONE
    assert ("spotted", "trainer") in captured
    assert ("interact", "trainer") in captured


def test_approach_walks_then_challenges_on_arrival(captured):
    behavior = TrainerSightBehavior(IdleBehavior(), can_challenge=lambda _id: True)
    npc = make_npc(direction="up", y=0.0)

    world = FakeWorld(sight=2)
    first = behavior.decide(npc, world, 0.1)
    assert first is not None
    assert first["type"] == "move"

    npc.motion.pixel_y = first["target_y"]  # controller moved it
    world.sight = 1
    second = behavior.decide(npc, world, 0.1)

    assert second is None
    assert behavior.state == behavior.DONE
    assert [e for e in captured if e[0] == "interact"] == [("interact", "trainer")]


def test_blocked_path_challenges_from_where_it_stands(captured):
    behavior = TrainerSightBehavior(IdleBehavior(), can_challenge=lambda _id: True)
    world = FakeWorld(sight=3, walkable=False)  # a wall/NPC in the way

    intent = behavior.decide(make_npc(), world, 0.1)

    assert intent is None
    assert behavior.state == behavior.DONE
    assert ("interact", "trainer") in captured


def test_done_trainer_goes_quiet(captured):
    behavior = TrainerSightBehavior(IdleBehavior(), can_challenge=lambda _id: True)
    behavior.state = behavior.DONE

    assert behavior.decide(make_npc(), FakeWorld(sight=1), 0.1) is None
    assert captured == []


# --- controller raycast -----------------------------------------------------


def make_controller(player_x, player_y, walls=()):
    """NpcController with a stubbed collision lookup (no GL context needed)."""
    from src.systems import npc_controller as module

    wall_cells = set(walls)
    module.arcade.get_sprites_at_point = lambda point, _tiles: (
        [object()] if (round(point[0]), round(point[1])) in wall_cells else []
    )
    return module.NpcController(
        npcs=arcade.SpriteList(),
        movement_system=None,
        collision_tiles=None,
        player_state=SimpleNamespace(pixel_x=player_x, pixel_y=player_y, moving=False),
        map_width=1000,
        map_height=1000,
    )


@pytest.fixture(autouse=True)
def restore_arcade():
    from src.systems import npc_controller as module

    original = module.arcade.get_sprites_at_point
    yield
    module.arcade.get_sprites_at_point = original


def test_line_of_sight_finds_player_straight_ahead():
    npc = make_npc(direction="right", x=0.0, y=0.0)
    controller = make_controller(player_x=TILE_SIZE * 3, player_y=0.0)
    assert controller.line_of_sight(npc, 4) == 3


def test_line_of_sight_ignores_player_beyond_range():
    npc = make_npc(direction="right", x=0.0, y=0.0)
    controller = make_controller(player_x=TILE_SIZE * 5, player_y=0.0)
    assert controller.line_of_sight(npc, 4) is None


def test_line_of_sight_ignores_player_off_the_line():
    npc = make_npc(direction="right", x=0.0, y=0.0)
    controller = make_controller(player_x=TILE_SIZE * 2, player_y=TILE_SIZE)
    assert controller.line_of_sight(npc, 4) is None


def test_wall_blocks_line_of_sight():
    npc = make_npc(direction="right", x=0.0, y=0.0)
    controller = make_controller(
        player_x=TILE_SIZE * 3, player_y=0.0, walls=[(TILE_SIZE * 2, 0)]
    )
    assert controller.line_of_sight(npc, 4) is None


def test_line_of_sight_only_looks_where_the_npc_faces():
    # Player sits two tiles to the *right* of the NPC at the origin.
    controller = make_controller(player_x=TILE_SIZE * 2, player_y=0.0)
    assert controller.line_of_sight(make_npc(direction="right", x=0.0, y=0.0), 4) == 2
    assert controller.line_of_sight(make_npc(direction="left", x=0.0, y=0.0), 4) is None
    assert controller.line_of_sight(make_npc(direction="up", x=0.0, y=0.0), 4) is None


# --- make_behavior wiring ---------------------------------------------------


def test_make_behavior_without_policy_is_unwrapped():
    assert isinstance(make_behavior({"behavior": "wander"}), WanderBehavior)


def test_make_behavior_wraps_when_policy_given():
    behavior = make_behavior({"behavior": "wander"}, can_challenge=lambda _id: True)
    assert isinstance(behavior, TrainerSightBehavior)
    assert isinstance(behavior.inner, WanderBehavior)


def test_sight_range_zero_opts_out():
    behavior = make_behavior({"sight_range": 0}, can_challenge=lambda _id: True)
    assert isinstance(behavior, IdleBehavior)


def test_sight_range_is_read_from_properties():
    behavior = make_behavior({"sight_range": 7}, can_challenge=lambda _id: True)
    assert isinstance(behavior, TrainerSightBehavior)
    assert behavior.sight_range == 7


# --- can_walk ----------------------------------------------------------------


def make_walkable_controller(player_x=1000.0, player_y=1000.0, npcs=(), wall_cells=()):
    """NpcController with stubbed collision lookup — mirrors make_controller
    but exposes npcs/player position for can_walk's own checks."""
    from src.systems import npc_controller as module

    cells = set(wall_cells)
    module.arcade.get_sprites_at_point = lambda point, _tiles: (
        [object()] if (round(point[0]), round(point[1])) in cells else []
    )
    return module.NpcController(
        npcs=cast(arcade.SpriteList, list(npcs)),
        movement_system=None,
        collision_tiles=None,
        player_state=SimpleNamespace(pixel_x=player_x, pixel_y=player_y, moving=False),
        map_width=1000,
        map_height=1000,
    )


def test_can_walk_out_of_bounds_returns_false():
    controller = make_walkable_controller()
    assert controller.can_walk(-1, 50, asking=None) is False
    assert controller.can_walk(50, -1, asking=None) is False
    assert controller.can_walk(2000, 50, asking=None) is False
    assert controller.can_walk(50, 2000, asking=None) is False


def test_can_walk_blocked_by_static_collision():
    controller = make_walkable_controller(wall_cells=[(16, 16)])
    assert controller.can_walk(16, 16, asking=None) is False


def test_can_walk_blocked_by_player_position():
    controller = make_walkable_controller(player_x=16.0, player_y=16.0)
    assert controller.can_walk(16, 16, asking=None) is False


def test_can_walk_blocked_by_other_npc():
    other = SimpleNamespace(
        motion=SimpleNamespace(pixel_x=16.0, pixel_y=16.0, moving=False)
    )
    controller = make_walkable_controller(npcs=[other])
    assert controller.can_walk(16, 16, asking=None) is False


def test_can_walk_ignores_the_asking_npc_itself():
    asking = SimpleNamespace(
        motion=SimpleNamespace(pixel_x=16.0, pixel_y=16.0, moving=False)
    )
    controller = make_walkable_controller(npcs=[asking])
    assert controller.can_walk(16, 16, asking=asking) is True


def test_can_walk_open_cell_returns_true():
    controller = make_walkable_controller()
    assert controller.can_walk(500, 500, asking=None) is True


# --- _apply_intent -------------------------------------------------------------


def test_apply_intent_none_is_noop():
    controller = make_walkable_controller()
    npc = SimpleNamespace(
        motion=SimpleNamespace(direction="down"), set_idle=MagicMock()
    )
    controller._apply_intent(npc, None)
    npc.set_idle.assert_not_called()


def test_apply_intent_turn_updates_direction_and_idle_texture():
    controller = make_walkable_controller()
    npc = SimpleNamespace(
        motion=SimpleNamespace(direction="down"), set_idle=MagicMock()
    )
    controller._apply_intent(npc, {"type": "turn", "direction": "left"})
    assert npc.motion.direction == "left"
    npc.set_idle.assert_called_once_with("left")


def test_apply_intent_move_begins_movement_via_movement_system():
    controller = make_walkable_controller()
    controller.movement_system = MagicMock()
    npc = SimpleNamespace(motion=SimpleNamespace(direction="down"))
    intent = {"type": "move", "direction": "up", "target_y": 50.0}

    controller._apply_intent(npc, intent)

    assert npc.motion.direction == "up"
    controller.movement_system.begin.assert_called_once_with(npc.motion, intent)


def test_apply_intent_move_keeps_current_direction_if_absent():
    controller = make_walkable_controller()
    controller.movement_system = MagicMock()
    npc = SimpleNamespace(motion=SimpleNamespace(direction="down"))

    controller._apply_intent(npc, {"type": "move", "target_y": 50.0})

    assert npc.motion.direction == "down"


# --- update ----------------------------------------------------------------------


def make_fake_npc(moving=False, direction="down"):
    return SimpleNamespace(
        motion=SimpleNamespace(moving=moving, direction=direction),
        behavior=MagicMock(),
        sync_sprite=MagicMock(),
        update_animation=MagicMock(),
        set_idle=MagicMock(),
    )


def test_update_asks_behavior_only_when_not_moving():
    npc = make_fake_npc(moving=False)
    npc.behavior.decide.return_value = None
    controller = make_walkable_controller(npcs=[npc])
    controller.movement_system = MagicMock()

    controller.update(0.1)

    npc.behavior.decide.assert_called_once_with(npc, controller, 0.1)
    controller.movement_system.advance.assert_called_once_with(0.1, npc.motion)
    npc.sync_sprite.assert_called_once()
    npc.update_animation.assert_called_once()


def test_update_skips_behavior_while_already_moving():
    npc = make_fake_npc(moving=True)
    controller = make_walkable_controller(npcs=[npc])
    controller.movement_system = MagicMock()

    controller.update(0.1)

    npc.behavior.decide.assert_not_called()
    controller.movement_system.advance.assert_called_once_with(0.1, npc.motion)


def test_update_applies_decided_intent():
    npc = make_fake_npc(moving=False)
    npc.behavior.decide.return_value = {"type": "turn", "direction": "up"}
    controller = make_walkable_controller(npcs=[npc])
    controller.movement_system = MagicMock()

    controller.update(0.1)

    assert npc.motion.direction == "up"
    npc.set_idle.assert_called_once_with("up")
