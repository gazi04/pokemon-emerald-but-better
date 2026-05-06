import arcade

class PlayerSprites:
    def __init__(self):
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
        
    def getIdle(self, direction):
        return self.idleTextures[direction]

    def getWalkFrame(self, direction, frame_index):
        return self.walkTextures[direction][frame_index % 4]