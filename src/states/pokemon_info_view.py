import arcade
from src.core.data_loader import DataLoader
from src.model.player import PlayerPokemon
from src.ui.pokemon_informacion import PokemonInformacion
from data.config import Config
from typing import Optional

CONFIG = Config.load()


class PokemonInfoView(arcade.View):
    def __init__(
        self,
        previous_view: arcade.View,
        data_loader: DataLoader,
        pokemon: Optional[PlayerPokemon] = None,
    ):
        super().__init__()
        self.previous_view = previous_view

        self.ui = PokemonInformacion(pokemon, data_loader)

    def on_draw(self):
        self.clear()
        self.ui.draw()

    def on_key_press(self, symbol: int, modifiers: int):
        if self._is_pressed(CONFIG.controls.cancel, symbol):
            self.window.show_view(self.previous_view)
        elif self._is_pressed(CONFIG.controls.right, symbol):
            self.ui.nextTab()
        elif self._is_pressed(CONFIG.controls.left, symbol):
            self.ui.prevTab()

    def _is_pressed(self, config_key: str, symbol: int) -> bool:
        return getattr(arcade.key, config_key, None) == symbol
