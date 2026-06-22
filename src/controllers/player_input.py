from src.model.state.player_motion import PlayerMotion
from src.constants import TILE_SIZE
from src.core.event_bus import global_bus
from src.core.events import NpcInteractEvent
import arcade


class PlayerInput:
    """
    Controller layer: Translates hardware input into semantic intents (state change requests).
    """

    def __init__(self):
        self._interact_pressed_last_frame = False

    def process_input(
        self,
        player_state: PlayerMotion,
        keys: set,
        controls_config,
        collision_tiles,
        transitions,
        npcs=None,
    ):
        """
        Reads keyboard/gamepad and requests a state change.
        Returns an intent dictionary or None.
        """
        if player_state.moving:
            return None

        interact_pressed = self._is_pressed(controls_config.interact, keys)
        if (
            interact_pressed
            and not self._interact_pressed_last_frame
            and npcs is not None
        ):
            dx, dy = self._facing_offset(player_state.direction)
            for step in (1, 2):
                hit = arcade.get_sprites_at_point(
                    (
                        player_state.pixel_x + dx * step,
                        player_state.pixel_y + dy * step,
                    ),
                    npcs,
                )
                if hit:
                    global_bus.publish(NpcInteractEvent(npc_id=hit[0].npc_id))
                    self._interact_pressed_last_frame = True
                    return None
        self._interact_pressed_last_frame = interact_pressed

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

            # Block if an NPC stands on the target tile
            if npcs is not None and arcade.get_sprites_at_point(
                (target_x, target_y), npcs
            ):
                return {"type": "turn", "direction": new_dir}

            # Check collisions
            hit_list = arcade.get_sprites_at_point(
                (target_x, target_y), collision_tiles
            )
            if not hit_list:
                return {"type": "move", "target_x": target_x, "target_y": target_y}
            else:
                return {"type": "turn", "direction": new_dir}

        return None

    def _facing_offset(self, direction: str) -> tuple[int, int]:
        return {
            "up": (0, TILE_SIZE),
            "down": (0, -TILE_SIZE),
            "left": (-TILE_SIZE, 0),
            "right": (TILE_SIZE, 0),
        }.get(direction, (0, 0))

    def _is_pressed(self, config_key, keys: set) -> bool:
        key_code = getattr(arcade.key, config_key, None)
        return key_code is not None and key_code in keys
