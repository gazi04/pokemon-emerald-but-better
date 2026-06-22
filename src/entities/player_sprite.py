import arcade
from src.model.state.player_motion import PlayerMotion


class PlayerSprite(arcade.Sprite):
    def __init__(self):
        super().__init__(scale=1.9)
        self.idleTextures = {
            "down": arcade.load_texture(
                "assets/sprite/player/idle/brendan_idle_down.png"
            ),
            "up": arcade.load_texture("assets/sprite/player/idle/brendan_idle_up.png"),
            "left": arcade.load_texture(
                "assets/sprite/player/idle/brendan_idle_left.png"
            ),
        }
        self.idleTextures["right"] = self.idleTextures["left"].flip_left_right()

        self.walkTextures = {
            "down": [
                arcade.load_texture(
                    "assets/sprite/player/walk_anim/brendan_walk_down1.png"
                ),
                self.idleTextures["down"],
                arcade.load_texture(
                    "assets/sprite/player/walk_anim/brendan_walk_down2.png"
                ),
                self.idleTextures["down"],
            ],
            "up": [
                arcade.load_texture(
                    "assets/sprite/player/walk_anim/brendan_walk_up1.png"
                ),
                self.idleTextures["up"],
                arcade.load_texture(
                    "assets/sprite/player/walk_anim/brendan_walk_up2.png"
                ),
                self.idleTextures["up"],
            ],
            "left": [
                arcade.load_texture(
                    "assets/sprite/player/walk_anim/brendan_walk_left1.png"
                ),
                self.idleTextures["left"],
                arcade.load_texture(
                    "assets/sprite/player/walk_anim/brendan_walk_left2.png"
                ),
                self.idleTextures["left"],
            ],
        }

        self.walkTextures["right"] = [
            tex.flip_left_right() for tex in self.walkTextures["left"]
        ]

    def sync_with_state(self, state: PlayerMotion):
        self.center_x = state.pixel_x
        self.center_y = state.pixel_y

        if state.moving:
            progress = int(state.move_progress * 4) % 4
            self.set_walk_frame(state.direction, progress)
        else:
            self.set_idle(state.direction)

    def draw(self):
        arcade.draw_sprite(self)

    def set_idle(self, direction):
        if direction in self.idleTextures:
            self.texture = self.idleTextures[direction]

    def set_walk_frame(self, direction, progress):
        if direction in self.walkTextures:
            self.texture = self.walkTextures[direction][progress % 4]
