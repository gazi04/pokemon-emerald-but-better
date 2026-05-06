import arcade
import random
from src.util import getPokemon
from src.util import getEnc
from src.constants import TILE_SIZE, ENCOUNTER_RATE, MOVE_DURATION, MAP_HEIGHT
from src.core.gameContext import dataLoader


class Player(arcade.Sprite):
    def __init__(self):
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
        self.map = "littleroot_town"

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

        self.center_x = 0
        self.center_y = 0

        self.target_x = self.center_x
        self.target_y = self.center_y

        self.start_x = self.center_x
        self.start_y = self.center_y

        self.moving = False
        self.move_progress = 0.0
        self.move_duration = MOVE_DURATION

    def update(
        self, delta_time, keys, collision_tiles, bush, transitions, controlsConfig
    ):
        # print((self.center_x, self.center_y))
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

                hit_bush = arcade.get_sprites_at_point(
                    (self.center_x, self.center_y), bush
                )

                if hit_bush:
                    if random.random() < ENCOUNTER_RATE:
                        pokemonList = getEnc()[self.map]["grass"]

                        pokemon = random.choices(
                            pokemonList, weights=[p["weight"] for p in pokemonList]
                        )[0]
                        pokemon_data = dataLoader.getPokemon(pokemon["name"])
                        pokemon_lvl = random.randint(
                            pokemon["levels"][0], pokemon["levels"][1]
                        )
                        return {
                            "type": "encounter",
                            "name": pokemon["name"],
                            "data": pokemon_data,
                            "level": pokemon_lvl,
                        }

        # ====================== INPUT ======================
        else:
            new_dir = None
            dx = dy = 0

            if self.is_pressed(controlsConfig.up, keys):
                new_dir, dy = "up", TILE_SIZE
            elif self.is_pressed(controlsConfig.down, keys):
                new_dir, dy = "down", -TILE_SIZE
            elif self.is_pressed(controlsConfig.left, keys):
                new_dir, dx = "left", -TILE_SIZE
            elif self.is_pressed(controlsConfig.right, keys):
                new_dir, dx = "right", TILE_SIZE

            if new_dir:
                self.direction = new_dir
                target_x = self.center_x + dx
                target_y = self.center_y + dy

                hitTransitions = arcade.get_sprites_at_point(
                    (target_x, target_y), transitions
                )

                if hitTransitions:
                    # print(target_x, target_y)
                    return {
                        "type": "transition",
                        "map": hitTransitions[0].properties["destination map"],
                        "x": hitTransitions[0].properties["x"],
                        "y": hitTransitions[0].properties["y"],
                    }

                # Collision
                hit_list = arcade.get_sprites_at_point(
                    (target_x, target_y), collision_tiles
                )

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

    def teleportPlayer(self, x, y):
        self.center_x = x * 2
        self.center_y = y / 2 - 110
        
        print((self.center_x, self.center_y))

    def draw(self):
        arcade.draw_sprite(self)

    def is_pressed(self, configKey, keys):
        keyCode = getattr(arcade.key, configKey, None)

        return keyCode is not None and keyCode in keys

    def getPosition(self):
        return (self.center_x, self.center_y)
