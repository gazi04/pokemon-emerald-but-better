from src.model.player import PlayerState
from src.constants import TILE_SIZE
import arcade


class PlayerInput:
    """
    Controller layer: Translates hardware input into semantic intents (state change requests).
    """

    def process_input(
        self,
        player_state: PlayerState,
        keys: set,
        controls_config,
        collision_tiles,
        transitions,
    ):
        """
        Reads keyboard/gamepad and requests a state change.
        Returns an intent dictionary or None.
        """
        if player_state.moving:
            return None

        new_dir = None
        dx = dy = 0

        if self._is_pressed(controls_config.up, keys):
            new_dir, dy = "up", TILE_SIZE
        elif self._is_pressed(controls_config.down, keys):
            new_dir, dy = "down", -TILE_SIZE
        elif self._is_pressed(controls_config.left, keys):
            new_dir, dx = "left", -TILE_SIZE
        elif self._is_pressed(controls_config.right, keys):
            new_dir, dx = "right", TILE_SIZE

        if new_dir:
            player_state.direction = new_dir
            target_x = player_state.pixel_x + dx
            target_y = player_state.pixel_y + dy

            # Check transitions
            hit_transitions = arcade.get_sprites_at_point(
                (target_x, target_y), transitions
            )
            if hit_transitions:
                return {
                    "type": "transition",
                    "map": hit_transitions[0].properties["destination map"],
                    "x": hit_transitions[0].properties["x"],
                    "y": hit_transitions[0].properties["y"],
                }

            # Check collisions
            hit_list = arcade.get_sprites_at_point(
                (target_x, target_y), collision_tiles
            )
            if not hit_list:
                return {"type": "move", "target_x": target_x, "target_y": target_y}
            else:
                return {"type": "turn", "direction": new_dir}

        return None

    def _is_pressed(self, config_key, keys: set) -> bool:
        key_code = getattr(arcade.key, config_key, None)
        return key_code is not None and key_code in keys
