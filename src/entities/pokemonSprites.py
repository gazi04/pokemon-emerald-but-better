import arcade
from src.entities.pokemonBattle import PokemonBattle
from src.model.pokemon import PokemonMove, PokemonProfile, PokemonStat
from src.model.player import PlayerPokemonMove, PlayerPokemon


class Pokemon(arcade.Sprite):
    def __init__(
        self,
        data: PokemonProfile,
        isEnemy: bool,
        playerPokemon: PlayerPokemon = None,
        name: str = None,
        moves: list = None,
        currentHp: int = None,
        level: int = None,
    ):
        sprite_path = data.sprites.front if isEnemy else data.sprites.back

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

    def draw(self):
        arcade.draw_sprite(self, pixelated=True)
