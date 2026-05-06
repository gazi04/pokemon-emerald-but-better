import arcade
from src.entities.pokemonBattle import PokemonBattle
from src.model.pokemon import PokemonMove, PokemonProfile, PokemonStat
from src.model.player import PlayerPokemonMove

class Pokemon(arcade.Sprite):
    def __init__(
        self, 
        name: str,
        data:PokemonProfile,
        moves:list[PlayerPokemonMove],
        level:int,
        isEnemy:bool,
        currentHp:int=0,
        exp:int=0,
    ):
        sprite_path = data.sprites.front if isEnemy else data.sprites.back
        
        super().__init__(sprite_path.strip(), scale=3.0)

        self.pokemonBattle = PokemonBattle(name, data, moves, level, isEnemy, currentHp, exp)

        if isEnemy:
            self.center_x = 580
            self.center_y = 400
        else:
            self.center_x = 210
            self.bottom = 168
    
    def draw(self):
        arcade.draw_sprite(self, pixelated=True)
    