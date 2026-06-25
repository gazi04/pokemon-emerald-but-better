import arcade
from typing import cast
from src.model.static.pokemon import PokemonSpecies, SpritePaths


class PokemonSprite(arcade.Sprite):
    def __init__(self, data: PokemonSpecies, is_enemy: bool):
        sprites = cast(SpritePaths, data.sprites)
        sprite_path = sprites.front if is_enemy else sprites.back

        super().__init__(sprite_path.strip(), scale=3.0)

        if is_enemy:
            self.center_x = 580
            self.center_y = 400
        else:
            self.center_x = 210
            self.bottom = 168

    def set_new_texture(self, file: str):
        self.texture = arcade.load_texture(file)
        self.bottom = 168

    def draw(self):
        arcade.draw_sprite(self, pixelated=True)
