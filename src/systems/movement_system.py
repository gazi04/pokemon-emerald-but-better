from typing import Optional

from src.model.motion.player_motion import PlayerMotion
from src.constants import TILE_SIZE
from src.core.event_bus import global_bus
from src.core.events import PlayerFinishedMoveEvent


WALK_DURATION = 0.25
RUN_DURATION  = 0.19

class MovementSystem:

    def update(
        self, delta_time: float, player_state: PlayerMotion, intent: Optional[dict]
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
            events.append({
                "type": "finished_moving",
                "x": player_state.pixel_x,
                "y": player_state.pixel_y,
            })

        return events

    def begin(self, state: PlayerMotion, intent: Optional[dict]) -> None:
        if intent and not state.moving and intent.get("type") == "move":
            state.moving = True
            state.move_progress = 0.0
            state.start_x = state.pixel_x
            state.start_y = state.pixel_y
            state.target_x = intent["target_x"]
            state.target_y = intent["target_y"]

    def advance(self, delta_time: float, state: PlayerMotion) -> bool:
        if not state.moving:
            return False

        duration = RUN_DURATION if state.is_running else WALK_DURATION
        state.move_progress += delta_time / duration

        progress = min(state.move_progress, 1.0)
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
