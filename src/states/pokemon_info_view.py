import arcade
from src.core.data_loader import DataLoader
from src.model.player import PlayerPokemon
from src.ui.components.pokemon_informacion import PokemonInformacion
from data.config import Config

CONFIG = Config.load()


class PokemonInfoView(arcade.View):
    def __init__(
        self,
        previous_view: arcade.View,
        pokemon: PlayerPokemon,
        data_loader: DataLoader,
    ):
        super().__init__()
        self.previous_view = previous_view

        profile = data_loader.getPokemon(pokemon.name)
        if profile is None:
            raise ValueError(f"No profile found for '{pokemon.name}'")

        self.ui = PokemonInformacion(pokemon, profile)

    def on_draw(self):
        self.clear()
        self.ui.draw()

    def on_key_press(self, symbol: int, modifiers: int):
        if self._is(CONFIG.controls.cancel, symbol):
            self.window.show_view(self.previous_view)
        elif self._is(CONFIG.controls.right, symbol):
            self.ui.nextTab()
        elif self._is(CONFIG.controls.left, symbol):
            self.ui.prevTab()

    def _is(self, config_key: str, symbol: int) -> bool:
        return getattr(arcade.key, config_key, None) == symbol
