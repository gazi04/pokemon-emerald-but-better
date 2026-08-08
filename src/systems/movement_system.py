from src.model.motion.player_motion import PlayerMotion
from src.model.motion.grid_motion import GridMotion
from src.constants import TILE_SIZE
from src.core.event_bus import global_bus
from src.core.events import PlayerFinishedMoveEvent


WALK_DURATION = 0.25
RUN_DURATION = 0.19


class MovementSystem:
    def update(
        self, delta_time: float, state: GridMotion, intent: dict | None
    ) -> list[dict]:
        events = []

        self.begin(state, intent)

        if self.advance(delta_time, state):
            if isinstance(state, PlayerMotion):
                global_bus.publish(
                    PlayerFinishedMoveEvent(
                        grid_x=state.grid_x,
                        grid_y=state.grid_y,
                        map_name=state.map_name,
                    )
                )

            events.append(
                {
                    "type": "finished_moving",
                    "x": state.pixel_x,
                    "y": state.pixel_y,
                }
            )

        return events

    def begin(self, state: GridMotion, intent: dict | None) -> None:
        if intent and not state.moving and intent.get("type") == "move":
            state.moving = True
            state.move_progress = 0.0
            state.start_x = state.pixel_x
            state.start_y = state.pixel_y
            state.target_x = intent["target_x"]
            state.target_y = intent["target_y"]

            if isinstance(state, PlayerMotion):
                state.is_hopping = bool(intent.get("hop"))

    def advance(self, delta_time: float, state: GridMotion) -> bool:
        if not state.moving:
            return False

        if isinstance(state, PlayerMotion):
            duration = RUN_DURATION if state.is_running else WALK_DURATION
        else:
            duration = WALK_DURATION

        # Clamp the stored progress, not just the local copy: a huge delta must
        # not leave a >1 value behind for animations to read.
        state.move_progress = min(state.move_progress + delta_time / duration, 1.0)

        progress = state.move_progress
        state.pixel_x = state.start_x + (state.target_x - state.start_x) * progress
        state.pixel_y = state.start_y + (state.target_y - state.start_y) * progress

        if state.move_progress >= 1.0:
            state.pixel_x = state.target_x
            state.pixel_y = state.target_y
            state.moving = False
            state.grid_x = round(state.pixel_x / TILE_SIZE)
            state.grid_y = round(state.pixel_y / TILE_SIZE)
            return True

        return False
