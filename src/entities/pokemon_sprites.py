import arcade
from typing import Optional, cast
from src.entities.pokemon_battle import PokemonBattle
from src.model.pokemon import PokemonProfile, PokemonSprites
from src.model.player import PlayerPokemon


class Pokemon(arcade.Sprite):
    def __init__(
        self,
        data: PokemonProfile,
        isEnemy: bool,
        playerPokemon: Optional[PlayerPokemon] = None,
        name: Optional[str] = None,
        moves: Optional[list] = None,
        currentHp: Optional[int] = None,
        level: Optional[int] = None,
    ):
        sprites = cast(PokemonSprites, data.sprites)
        sprite_path = sprites.front if isEnemy else sprites.back

        super().__init__(sprite_path.strip(), scale=3.0)

        self.pokemonBattle = PokemonBattle(
            data, isEnemy, playerPokemon, name, moves, currentHp, level
        )

        if isEnemy:
            self.center_x = 580
            self.center_y = 400
        else:
            self.center_x = 210
            self.bottom = 168
            
    def setNewTexture(self, file: str):
        self.texture = arcade.load_texture(file)
        self.bottom = 168
        
    def draw(self):
        arcade.draw_sprite(self, pixelated=True)
