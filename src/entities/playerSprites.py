import arcade


class PlayerSprites(arcade.Sprite):
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

    def draw(self):
        arcade.draw_sprite(self)

    def setIdle(self, direction):
        self.texture = self.idleTextures[direction]

    def setWalkFrame(self, direction, progress):
        self.texture = self.walkTextures[direction][progress % 4]
