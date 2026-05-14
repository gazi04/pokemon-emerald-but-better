import arcade
import random
from src.util import getEnc
from src.constants import TILE_SIZE, ENCOUNTER_RATE, MOVE_DURATION, MAP_HEIGHT
from src.core.gameContext import dataLoader
from src.entities.playerSprites import PlayerSprites


class Player:
    def __init__(self):
        self.sprites = PlayerSprites()

        self.map = "littleroot_town"

        self.direction = "down"
        self.sprites.setIdle(self.direction)

        self.sprites.center_x = 0
        self.sprites.center_y = 0

        self.target_x = self.sprites.center_x
        self.target_y = self.sprites.center_y

        self.start_x = self.sprites.center_x
        self.start_y = self.sprites.center_y

        self.moving = False
        self.moveProgress = 0.0
        self.moveDuration = MOVE_DURATION

    def update(
        self, delta_time, keys, collisionTiles, bush, transitions, controlsConfig
    ):
        if self.moving:
            return self.movement(delta_time, bush)
        else:
            self.input(controlsConfig, keys, transitions, collisionTiles)

        return None

    def movement(self, delta_time, bush):
        self.moveProgress += delta_time / self.moveDuration

        if self.moveProgress >= 1.0:
            self.moveProgress = 1.0

        self.sprites.center_x = (
            self.start_x + (self.target_x - self.start_x) * self.moveProgress
        )
        self.sprites.center_y = (
            self.start_y + (self.target_y - self.start_y) * self.moveProgress
        )

        progress = int(self.moveProgress * 4) % 4
        self.sprites.setWalkFrame(self.direction, progress)

        if self.moveProgress >= 1.0:
            self.sprites.center_x = self.target_x
            self.sprites.center_y = self.target_y
            self.moving = False
            self.sprites.setIdle(self.direction)

            hit_bush = arcade.get_sprites_at_point(
                (self.sprites.center_x, self.sprites.center_y), bush
            )

            if not hit_bush:
                return None

            if random.random() < ENCOUNTER_RATE:
                pokemonList = getEnc()[self.map]["grass"]

                pokemon = random.choices(
                    pokemonList, weights=[p["weight"] for p in pokemonList]
                )[0]
                pokemon_data = dataLoader.getPokemon(pokemon["name"])
                pokemon_lvl = random.randint(pokemon["levels"][0], pokemon["levels"][1])
                return {
                    "type": "encounter",
                    "name": pokemon["name"],
                    "data": pokemon_data,
                    "level": pokemon_lvl,
                }

        return None

    def input(self, controlsConfig, keys, transitions, collisionTiles):
        newDir = None
        dx = dy = 0

        if self.is_pressed(controlsConfig.up, keys):
            newDir, dy = "up", TILE_SIZE
        elif self.is_pressed(controlsConfig.down, keys):
            newDir, dy = "down", -TILE_SIZE
        elif self.is_pressed(controlsConfig.left, keys):
            newDir, dx = "left", -TILE_SIZE
        elif self.is_pressed(controlsConfig.right, keys):
            newDir, dx = "right", TILE_SIZE

        if newDir:
            self.direction = newDir
            target_x = self.sprites.center_x + dx
            target_y = self.sprites.center_y + dy

            hitTransitions = arcade.get_sprites_at_point(
                (target_x, target_y), transitions
            )

            if hitTransitions:
                return {
                    "type": "transition",
                    "map": hitTransitions[0].properties["destination map"],
                    "x": hitTransitions[0].properties["x"],
                    "y": hitTransitions[0].properties["y"],
                }

            hit_list = arcade.get_sprites_at_point((target_x, target_y), collisionTiles)

            if not hit_list:
                self.moving = True
                self.moveProgress = 0.0

                self.start_x = self.sprites.center_x
                self.start_y = self.sprites.center_y

                self.target_x = target_x
                self.target_y = target_y

                self.sprites.setIdle(self.direction)
            else:
                self.sprites.setIdle(self.direction)

    def teleportPlayer(self, x, y):
        self.sprites.center_x = x * 2
        self.sprites.center_y = y / 2 - 110

    def draw(self):
        self.sprites.draw()

    def is_pressed(self, configKey, keys) -> bool:
        keyCode = getattr(arcade.key, configKey, None)

        return keyCode is not None and keyCode in keys

    def getPosition(self):
        return (self.sprites.center_x, self.sprites.center_y)
