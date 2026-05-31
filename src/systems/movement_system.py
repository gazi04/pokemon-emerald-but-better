from src.model.player import PlayerState
from src.constants import TILE_SIZE
from src.core.event_bus import global_bus
from src.core.events import PlayerFinishedMoveEvent


class MovementSystem:
    """
    Logic layer: Executes movement intent, updating pixel coordinates for the Sprite.
    """

    def update(
        self, delta_time: float, player_state: PlayerState, intent: dict
    ) -> list[dict]:
        events = []

        if intent and not player_state.moving:
            if intent["type"] == "move":
                player_state.moving = True
                player_state.move_progress = 0.0
                player_state.start_x = player_state.pixel_x
                player_state.start_y = player_state.pixel_y
                player_state.target_x = intent["target_x"]
                player_state.target_y = intent["target_y"]

        if player_state.moving:
            duration = (
                player_state.move_duration if player_state.move_duration > 0 else 0.25
            )

            player_state.move_progress += delta_time / duration
            if player_state.move_progress >= 1.0:
                player_state.move_progress = 1.0

            player_state.pixel_x = (
                player_state.start_x
                + (player_state.target_x - player_state.start_x)
                * player_state.move_progress
            )
            player_state.pixel_y = (
                player_state.start_y
                + (player_state.target_y - player_state.start_y)
                * player_state.move_progress
            )

            if player_state.move_progress >= 1.0:
                player_state.pixel_x = player_state.target_x
                player_state.pixel_y = player_state.target_y
                player_state.moving = False

                player_state.grid_x = round(player_state.pixel_x / TILE_SIZE)
                player_state.grid_y = round(player_state.pixel_y / TILE_SIZE)

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
