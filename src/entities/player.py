import arcade
import random
from src.util import getPokemon


class Player(arcade.Sprite):
    def __init__(self, x: int, y: int):
        super().__init__(scale=1.9)

        # ====================== LOAD TEXTURES ======================
        # Idle
        self.idle_textures = {
            "down": arcade.load_texture(
                "assets/sprite/player/idle/brendan_idle_down.png"
            ),
            "up": arcade.load_texture("assets/sprite/player/idle/brendan_idle_up.png"),
            "left": arcade.load_texture(
                "assets/sprite/player/idle/brendan_idle_left.png"
            ),
        }
        self.idle_textures["right"] = self.idle_textures["left"].flip_left_right()

        # Walk (2 frames → we make it 4-frame loop)
        self.walk_textures = {
            "down": [
                arcade.load_texture(
                    "assets/sprite/player/walk_anim/brendan_walk_down1.png"
                ),
                self.idle_textures["down"],
                arcade.load_texture(
                    "assets/sprite/player/walk_anim/brendan_walk_down2.png"
                ),
                self.idle_textures["down"],
            ],
            "up": [
                arcade.load_texture(
                    "assets/sprite/player/walk_anim/brendan_walk_up1.png"
                ),
                self.idle_textures["up"],
                arcade.load_texture(
                    "assets/sprite/player/walk_anim/brendan_walk_up2.png"
                ),
                self.idle_textures["up"],
            ],
            "left": [
                arcade.load_texture(
                    "assets/sprite/player/walk_anim/brendan_walk_left1.png"
                ),
                self.idle_textures["left"],
                arcade.load_texture(
                    "assets/sprite/player/walk_anim/brendan_walk_left2.png"
                ),
                self.idle_textures["left"],
            ],
        }

        # Create right by flipping left
        self.walk_textures["right"] = [
            tex.flip_left_right() for tex in self.walk_textures["left"]
        ]

        # ====================== PLAYER STATE ======================
        self.direction = "down"
        self.texture = self.idle_textures[self.direction]

        self.center_x = x * 32 + 16
        self.center_y = y * 32 + 16

        self.target_x = self.center_x
        self.target_y = self.center_y

        self.start_x = self.center_x
        self.start_y = self.center_y

        self.moving = False
        self.move_progress = 0.0
        self.move_duration = 0.2  # Pokémon-like speed

    def update(self, delta_time, keys, collision_tiles, bush):
        # ====================== MOVEMENT ======================
        if self.moving:
            self.move_progress += delta_time / self.move_duration

            if self.move_progress >= 1.0:
                self.move_progress = 1.0

            # Tile-perfect movement
            self.center_x = (
                self.start_x + (self.target_x - self.start_x) * self.move_progress
            )
            self.center_y = (
                self.start_y + (self.target_y - self.start_y) * self.move_progress
            )

            # Animation synced to movement
            frame_index = int(self.move_progress * 4) % 4
            self.texture = self.walk_textures[self.direction][frame_index]

            # Finish movement
            if self.move_progress >= 1.0:
                self.center_x = self.target_x
                self.center_y = self.target_y
                self.moving = False
                self.texture = self.idle_textures[self.direction]

        # ====================== INPUT ======================
        else:
            new_dir = None
            dx = dy = 0

            if arcade.key.UP in keys or arcade.key.W in keys:
                new_dir, dy = "up", 32
            elif arcade.key.DOWN in keys or arcade.key.S in keys:
                new_dir, dy = "down", -32
            elif arcade.key.LEFT in keys or arcade.key.A in keys:
                new_dir, dx = "left", -32
            elif arcade.key.RIGHT in keys or arcade.key.D in keys:
                new_dir, dx = "right", 32

            if new_dir:
                self.direction = new_dir
                target_x = self.center_x + dx
                target_y = self.center_y + dy

                # Collision
                hit_list = arcade.get_sprites_at_point(
                    (target_x, target_y), collision_tiles
                )
                hit_bush = arcade.get_sprites_at_point((target_x, target_y), bush)

                # Random encounter
                if hit_bush and not hit_list:
                    if random.random() < 0.15:
                        pokemon_string = hit_bush[0].properties.get("pokemon", "")
                        if pokemon_string:
                            possible = [p.strip() for p in pokemon_string.split(",")]
                            pokemon_name = random.choice(possible)
                            pokemon_data = getPokemon()[pokemon_name]
                            return (pokemon_name, pokemon_data)

                if not hit_list:
                    self.moving = True
                    self.move_progress = 0.0

                    self.start_x = self.center_x
                    self.start_y = self.center_y

                    self.target_x = target_x
                    self.target_y = target_y

                    self.texture = self.walk_textures[self.direction][0]
                else:
                    self.texture = self.idle_textures[self.direction]

        return None

    def draw(self):
        arcade.draw_sprite(self)

    def getPosition(self):
        return (self.center_x, self.center_y)
