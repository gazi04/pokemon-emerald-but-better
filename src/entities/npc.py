import arcade
from src.constants import TILE_SIZE
from src.model.grid_motion import GridMotion
from src.systems.npc_behaviors import Behavior, IdleBehavior


class Npc(arcade.Sprite):
    def __init__(self, texture, x, y, npc_id, behavior: Behavior = None, facing: str = "down"):
        super().__init__(texture, 1.9, x, y)
        self.npc_id = npc_id

        # Where the NPC was spawned — wander behaviors leash to this.
        self.home_x = x
        self.home_y = y

        self.motion = GridMotion(
            pixel_x=x,
            pixel_y=y,
            grid_x=round(x / TILE_SIZE),
            grid_y=round(y / TILE_SIZE),
            direction=facing,
        )

        self.behavior = behavior or IdleBehavior()

    def sync_sprite(self) -> None:
        """Push the motion's pixel position onto the arcade sprite."""
        self.center_x = self.motion.pixel_x
        self.center_y = self.motion.pixel_y
