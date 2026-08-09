"""The player-input decision for stepping into a ledge tile: hop with the
grain, wall against it, and never hop into an occupied landing."""

import arcade
import pytest

from src.constants import TILE_SIZE
from src.controllers.player_input import PlayerInput
from src.model.motion.player_motion import PlayerMotion


class Controls:
    up = "UP"
    down = "DOWN"
    left = "LEFT"
    right = "RIGHT"
    interact = "Z"
    run = "LSHIFT"
    cancel = "X"


class NoLayer:
    """A transitions/items stand-in that never matches."""

    def find(self, x, y):
        return None


class Ledge:
    """Every tile is a ledge of one fixed direction."""

    def __init__(self, direction):
        self.direction = direction

    def find(self, x, y):
        return self.direction


@pytest.fixture(scope="module")
def window():
    win = arcade.Window(60, 60, "test", visible=False)
    yield win
    win.close()


@pytest.fixture
def collision():
    return arcade.SpriteList()


def wall_at(collision, x, y):
    sprite = arcade.SpriteSolidColor(TILE_SIZE, TILE_SIZE, color=arcade.color.RED)
    sprite.center_x, sprite.center_y = x, y
    collision.append(sprite)


def press(direction):
    return {getattr(arcade.key, direction)}


def decide(collision, key, ledge_direction, px=100.0, py=100.0):
    state = PlayerMotion(pixel_x=px, pixel_y=py)
    return PlayerInput().process_input(
        state,
        press(key),
        Controls,
        collision,
        transitions=NoLayer(),
        npcs=None,
        items=None,
        ledges=Ledge(ledge_direction),
    )


# --- hopping with the grain -------------------------------------------------


def test_hop_down_over_a_down_ledge(window, collision):
    intent = decide(collision, "DOWN", ledge_direction="down")
    if intent is None:
        pytest.fail("The intent cant be None")

    assert intent["type"] == "move"
    assert intent["hop"] is True
    assert intent["target_x"] == 100.0
    assert intent["target_y"] == 100.0 - 2 * TILE_SIZE  # y-up: down decreases y


def test_hop_left_over_a_left_ledge(window, collision):
    intent = decide(collision, "LEFT", ledge_direction="left")
    if intent is None:
        pytest.fail("The intent cant be None")

    assert intent["hop"] is True
    assert intent["target_x"] == 100.0 - 2 * TILE_SIZE
    assert intent["target_y"] == 100.0


# --- blocked against the grain ----------------------------------------------


def test_cannot_climb_a_ledge_from_below(window, collision):
    # Facing up into a ledge whose one-way direction is down.
    intent = decide(collision, "UP", ledge_direction="down")
    assert intent == {"type": "turn", "direction": "up"}


def test_sideways_into_a_down_ledge_is_blocked(window, collision):
    intent = decide(collision, "RIGHT", ledge_direction="down")
    assert intent == {"type": "turn", "direction": "right"}


# --- landing must be clear --------------------------------------------------


def test_no_hop_when_the_landing_tile_is_a_wall(window, collision):
    wall_at(collision, 100.0, 100.0 - 2 * TILE_SIZE)  # two tiles down
    intent = decide(collision, "DOWN", ledge_direction="down")
    assert intent == {"type": "turn", "direction": "down"}


def test_wall_on_the_ledge_tile_itself_does_not_block_the_hop(window, collision):
    # The ledge tile can be solid terrain; the hop clears it. Only the landing
    # (two tiles out) needs to be free.
    wall_at(collision, 100.0, 100.0 - TILE_SIZE)  # one tile down: the ledge tile
    intent = decide(collision, "DOWN", ledge_direction="down")

    if intent is None:
        pytest.fail("The intent cant be None")

    assert intent["type"] == "move"
    assert intent["hop"] is True
