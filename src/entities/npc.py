import arcade
from src.constants import TILE_SIZE
from src.model.grid_motion import GridMotion
from src.systems.npc_behaviors import Behavior, IdleBehavior


class Npc(arcade.Sprite):
    def __init__(self, x, y, npc_id, behavior: Behavior = None, facing: str = "right"):
        super().__init__(scale=1.9, center_x=x, center_y=y)
        self.npc_id = npc_id

        self.idleTextures = {
            "down": arcade.load_texture(
                "assets/sprite/npc/default/idle/npc_idle_down.png"
            ),
            "up": arcade.load_texture("assets/sprite/npc/default/idle/npc_idle_up.png"),
            "left": arcade.load_texture(
                "assets/sprite/npc/default/idle/npc_idle_left.png"
            ),
        }
        self.idleTextures["right"] = self.idleTextures["left"].flip_left_right()

        self.walkTextures = {
            "down": [
                arcade.load_texture(
                    "assets/sprite/npc/default/walk_anim/npc_walk_down1.png"
                ),
                self.idleTextures["down"],
                arcade.load_texture(
                    "assets/sprite/npc/default/walk_anim/npc_walk_down2.png"
                ),
                self.idleTextures["down"],
            ],
            "up": [
                arcade.load_texture(
                    "assets/sprite/npc/default/walk_anim/npc_walk_up1.png"
                ),
                self.idleTextures["up"],
                arcade.load_texture(
                    "assets/sprite/npc/default/walk_anim/npc_walk_up2.png"
                ),
                self.idleTextures["up"],
            ],
            "left": [
                arcade.load_texture(
                    "assets/sprite/npc/default/walk_anim/npc_walk_left1.png"
                ),
                self.idleTextures["left"],
                arcade.load_texture(
                    "assets/sprite/npc/default/walk_anim/npc_walk_left2.png"
                ),
                self.idleTextures["left"],
            ],
        }

        self.walkTextures["right"] = [
            tex.flip_left_right() for tex in self.walkTextures["left"]
        ]
        
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
        self.set_idle(facing)

    def sync_sprite(self) -> None:
        """Push the motion's pixel position onto the arcade sprite."""
        self.center_x = self.motion.pixel_x
        self.center_y = self.motion.pixel_y
        
    def set_idle(self, direction):
        if direction in self.idleTextures:
            self.texture = self.idleTextures[direction]

    def set_walk_frame(self, direction, progress):
        if direction in self.walkTextures:
            self.texture = self.walkTextures[direction][progress % 4]

    def update_animation(self) -> None:
        """Pick the texture for the current motion state: walking steps the
        walk cycle by move progress, otherwise hold the idle pose."""
        if self.motion.moving:
            frame = min(int(self.motion.move_progress * 4), 3)
            self.set_walk_frame(self.motion.direction, frame)
        else:
            self.set_idle(self.motion.direction)
