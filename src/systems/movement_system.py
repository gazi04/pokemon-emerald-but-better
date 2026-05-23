from src.model.player import PlayerState

class MovementSystem:
    """
    Logic layer: Executes movement intent, updating pixel coordinates for the Sprite.
    """
    def update(self, delta_time: float, player_state: PlayerState, intent: dict) -> list[dict]:
        """
        Updates the player state.
        Returns a list of resulting events (like "finished_moving").
        """
        events = []

        # Start a new movement if triggered
        if intent and not player_state.moving:
            if intent["type"] == "move":
                player_state.moving = True
                player_state.move_progress = 0.0
                player_state.start_x = player_state.pixel_x
                player_state.start_y = player_state.pixel_y
                player_state.target_x = intent["target_x"]
                player_state.target_y = intent["target_y"]

        # Run lerping if moving
        if player_state.moving:
            duration = player_state.move_duration
            if duration <= 0:
                duration = 0.25 # Fallback
                
            player_state.move_progress += delta_time / duration

            if player_state.move_progress >= 1.0:
                player_state.move_progress = 1.0

            # Lerp coordinates
            player_state.pixel_x = player_state.start_x + (player_state.target_x - player_state.start_x) * player_state.move_progress
            player_state.pixel_y = player_state.start_y + (player_state.target_y - player_state.start_y) * player_state.move_progress

            # If finished moving
            if player_state.move_progress >= 1.0:
                player_state.pixel_x = player_state.target_x
                player_state.pixel_y = player_state.target_y
                player_state.moving = False
                
                # Emit event
                events.append({
                    "type": "finished_moving",
                    "x": player_state.pixel_x,
                    "y": player_state.pixel_y
                })

        return events
