"""Trainer line-of-sight: spotting the player, walking over, and challenging."""
from types import SimpleNamespace

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
        npcs=[],
        movement_system=None,
        collision_tiles=None,
        player_state=SimpleNamespace(
            pixel_x=player_x, pixel_y=player_y, moving=False
        ),
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
    assert behavior.sight_range == 7
