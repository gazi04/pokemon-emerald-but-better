from src.model.motion.player_motion import PlayerMotion
from src.constants import TILE_SIZE
from src.core.event_bus import global_bus
from src.core.events import PlayerFinishedMoveEvent


class MovementSystem:
    """
    Logic layer: Executes movement intent, updating pixel coordinates for the Sprite.
    Works on any object exposing the GridMotion/PlayerMotion movement fields,
    so it drives both the player and NPCs.
    """

    def update(
        self, delta_time: float, player_state: PlayerMotion, intent: dict | None
    ) -> list[dict]:
        events = []

        self.begin(player_state, intent)

        if self.advance(delta_time, player_state):
            global_bus.publish(
                PlayerFinishedMoveEvent(
                    grid_x=player_state.grid_x,
                    grid_y=player_state.grid_y,
                    map_name=player_state.map_name,
                )
            )
            events.append(
                {
                    "type": "finished_moving",
                    "x": player_state.pixel_x,
                    "y": player_state.pixel_y,
                }
            )

        return events

    def begin(self, state, intent) -> None:
        """Start a new step if a 'move' intent is given and we're idle."""
        if intent and not state.moving and intent.get("type") == "move":
            state.moving = True
            state.move_progress = 0.0
            state.start_x = state.pixel_x
            state.start_y = state.pixel_y
            state.target_x = intent["target_x"]
            state.target_y = intent["target_y"]

    def advance(self, delta_time: float, state) -> bool:
        """
        Progress an in-flight step. Returns True on the frame a step completes.
        """
        if not state.moving:
            return False

        duration = state.move_duration if state.move_duration > 0 else 0.25

        state.move_progress += delta_time / duration
        if state.move_progress >= 1.0:
            state.move_progress = 1.0

        state.pixel_x = (
            state.start_x + (state.target_x - state.start_x) * state.move_progress
        )
        state.pixel_y = (
            state.start_y + (state.target_y - state.start_y) * state.move_progress
        )

        if state.move_progress >= 1.0:
            state.pixel_x = state.target_x
            state.pixel_y = state.target_y
            state.moving = False
            state.grid_x = round(state.pixel_x / TILE_SIZE)
            state.grid_y = round(state.pixel_y / TILE_SIZE)
            return True

        return False
