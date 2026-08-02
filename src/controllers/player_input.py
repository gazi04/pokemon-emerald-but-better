from src.model.motion.player_motion import PlayerMotion
from src.constants import TILE_SIZE
from src.core.event_bus import global_bus
from src.core.events import ItemPickedUpEvent, NpcInteractEvent
import arcade


class PlayerInput:
    """
    Controller layer: translates hardware input into semantic intents
    (state change requests).
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
        items=None,
        ledges=None,
    ) -> dict | None:
        """
        Reads keyboard/gamepad and requests a state change.
        Returns an intent dictionary or None.
        """
        if player_state.moving:
            return None

        interact_pressed = self._is_pressed(controls_config.interact, keys)
        if interact_pressed and not self._interact_pressed_last_frame:
            dx, dy = self._facing_offset(player_state.direction)

            if npcs is not None:
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

            # Ground items sit on the tile you're facing, like the real games.
            if items is not None:
                item = items.find(
                    player_state.pixel_x + dx, player_state.pixel_y + dy
                )
                if item is not None:
                    global_bus.publish(
                        ItemPickedUpEvent(key=item.key, item_id=item.item_id)
                    )
                    self._interact_pressed_last_frame = True
                    return None
        self._interact_pressed_last_frame = interact_pressed

        player_state.is_running = self._is_pressed(controls_config.run, keys)

        new_dir = self._pressed_direction(controls_config, keys)

        if new_dir:
            dx, dy = self._facing_offset(new_dir)
            player_state.direction = new_dir
            target_x = player_state.pixel_x + dx
            target_y = player_state.pixel_y + dy

            # Check transitions — the layer handles rectangle regions and legacy
            # gid doors; MapManager owns what the properties mean.
            transition_props = transitions.find(target_x, target_y)
            if transition_props is not None:
                return {"type": "transition", "properties": transition_props}

            # Block if an NPC stands on the target tile
            if npcs is not None and arcade.get_sprites_at_point(
                (target_x, target_y), npcs
            ):
                return {"type": "turn", "direction": new_dir}

            # Ground items are solid — you stop in front and press interact,
            # rather than walking over them.
            if items is not None and items.find(target_x, target_y) is not None:
                return {"type": "turn", "direction": new_dir}

            # Ledges: hoppable one way, a wall every other way.
            if ledges is not None:
                ledge_dir = ledges.find(target_x, target_y)
                if ledge_dir is not None:
                    return self._resolve_ledge(
                        player_state, new_dir, dx, dy, ledge_dir, collision_tiles
                    )

            # Check collisions
            hit_list = arcade.get_sprites_at_point(
                (target_x, target_y), collision_tiles
            )
            if not hit_list:
                return {"type": "move", "target_x": target_x, "target_y": target_y}
            else:
                return {"type": "turn", "direction": new_dir}

        return None

    def _resolve_ledge(
        self, player_state, new_dir, dx, dy, ledge_dir, collision_tiles
    ) -> dict:
        """Turn a step into a ledge tile into either a hop or a block.

        You may only cross a ledge in its authored direction; approach it from
        any other side and it's a wall. A valid hop clears the ledge and lands
        two tiles out — but only if that landing tile is itself free.
        """
        if new_dir != ledge_dir:
            return {"type": "turn", "direction": new_dir}

        landing_x = player_state.pixel_x + dx * 2
        landing_y = player_state.pixel_y + dy * 2

        if arcade.get_sprites_at_point((landing_x, landing_y), collision_tiles):
            return {"type": "turn", "direction": new_dir}

        return {
            "type": "move",
            "target_x": landing_x,
            "target_y": landing_y,
            "hop": True,
        }
        
    def _pressed_direction(self, controls_config, keys: set) -> str | None:
        """First direction key held, in up/down/left/right priority order —
        matches the priority the old if/elif chain gave simultaneous presses."""
        for direction in ("up", "down", "left", "right"):
            if self._is_pressed(getattr(controls_config, direction), keys):
                return direction
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
