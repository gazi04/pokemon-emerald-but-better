from src.constants import TILE_SIZE
from src.core.event_bus import global_bus
from src.core.events import PlayerFinishedMoveEvent
from src.model.motion.player_motion import PlayerMotion
from src.systems.movement_system import MovementSystem


def make_state(px=0.0, py=0.0, gx=0, gy=0):
    return PlayerMotion(
        pixel_x=px, pixel_y=py, grid_x=gx, grid_y=gy, map_name="littleroot_town"
    )


def make_intent(target_x, target_y):
    return {"type": "move", "target_x": float(target_x), "target_y": float(target_y)}


def test_no_intent_state_unchanged():
    system = MovementSystem()
    state = make_state(px=32.0, py=32.0)
    result = system.update(0.1, state, None)
    assert not state.moving
    assert state.pixel_x == 32.0
    assert result == []


def test_move_intent_starts_movement():
    system = MovementSystem()
    state = make_state(px=0.0, py=0.0)
    system.update(0.0, state, make_intent(32, 0))
    assert state.moving
    assert state.target_x == 32.0


def test_partial_delta_interpolates_position():
    system = MovementSystem()
    state = make_state(px=0.0, py=0.0)
    system.update(0.0, state, make_intent(32, 0))
    system.update(0.1, state, None)  # partial progress (duration ~0.25)
    assert state.moving
    assert 0.0 < state.pixel_x < 32.0
    assert 0.0 < state.move_progress < 1.0


def test_movement_completes_on_full_duration():
    system = MovementSystem()
    state = make_state(px=0.0, py=0.0)
    system.update(0.0, state, make_intent(32, 0))
    system.update(1.0, state, None)  # big delta → completes
    assert not state.moving
    assert state.pixel_x == 32.0


def test_overshoot_clamps_to_target():
    system = MovementSystem()
    state = make_state(px=0.0, py=0.0)
    system.update(0.0, state, make_intent(32, 0))
    system.update(999.0, state, None)
    assert state.pixel_x == 32.0
    assert state.move_progress == 1.0


def test_grid_coords_updated_on_completion():
    system = MovementSystem()
    target_x = 2 * TILE_SIZE
    target_y = 3 * TILE_SIZE
    state = make_state(px=0.0, py=0.0)
    system.update(0.0, state, make_intent(target_x, target_y))
    system.update(1.0, state, None)
    assert state.grid_x == 2
    assert state.grid_y == 3


def test_finished_moving_event_published_on_completion():
    system = MovementSystem()
    state = make_state(px=0.0, py=0.0)
    received = []
    global_bus.subscribe(PlayerFinishedMoveEvent, received.append)

    system.update(0.0, state, make_intent(TILE_SIZE, 0))
    system.update(1.0, state, None)

    assert len(received) == 1
    assert received[0].grid_x == 1
    assert received[0].grid_y == 0
    assert received[0].map_name == "littleroot_town"


def test_return_value_contains_finished_moving_on_completion():
    system = MovementSystem()
    state = make_state(px=0.0, py=0.0)
    system.update(0.0, state, make_intent(32, 0))
    result = system.update(1.0, state, None)
    assert len(result) == 1
    assert result[0]["type"] == "finished_moving"


def test_no_return_event_while_still_moving():
    system = MovementSystem()
    state = make_state(px=0.0, py=0.0)
    system.update(0.0, state, make_intent(32, 0))
    result = system.update(0.05, state, None)  # partial
    assert result == []


def test_movement_along_y_axis_only():
    system = MovementSystem()
    state = make_state(px=0.0, py=0.0)
    system.update(0.0, state, make_intent(0, TILE_SIZE))
    system.update(1.0, state, None)
    assert not state.moving
    assert state.pixel_y == float(TILE_SIZE)
    assert state.pixel_x == 0.0


def test_zero_distance_intent_does_not_crash():
    system = MovementSystem()
    state = make_state(px=0.0, py=0.0)
    system.update(0.0, state, make_intent(0, 0))
    system.update(0.1, state, None)
    assert state.pixel_x == 0.0
    assert state.pixel_y == 0.0


# --- ledge hop --------------------------------------------------------------


def test_hop_intent_sets_is_hopping():
    system = MovementSystem()
    state = make_state(px=0.0, py=0.0)

    intent = make_intent(0, 2 * TILE_SIZE)
    intent["hop"] = True
    system.update(0.0, state, intent)

    assert state.moving
    assert state.is_hopping


def test_plain_move_clears_is_hopping():
    system = MovementSystem()
    state = make_state(px=0.0, py=0.0)
    state.is_hopping = True  # leftover from a previous hop

    system.update(0.0, state, make_intent(TILE_SIZE, 0))

    assert not state.is_hopping


def test_hop_lands_two_tiles_away():
    system = MovementSystem()
    state = make_state(px=0.0, py=2 * TILE_SIZE)

    intent = make_intent(0, 0)  # hop straight down two tiles
    intent["hop"] = True
    system.update(0.0, state, intent)
    system.update(1.0, state, None)

    assert not state.moving
    assert state.pixel_y == 0.0
    assert state.grid_y == 0
