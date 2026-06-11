import arcade
from src.core.data_loader import DataLoader
from src.model.player import PlayerPokemon
from src.ui.pokemon_information_ui import PokemonInformationUI
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
        super().__init__(background_color=(0, 104, 96))
        self.previous_view = previous_view

        self.ui = PokemonInformationUI(pokemon, data_loader)

    def on_draw(self):
        self.clear()
        self.ui.draw()

    def on_key_press(self, key: int, modifiers: int):
        if self._is_pressed(CONFIG.controls.cancel, key):
            self.window.show_view(self.previous_view)
        elif self._is_pressed(CONFIG.controls.right, key):
            self.ui.next_tab()
        elif self._is_pressed(CONFIG.controls.left, key):
            self.ui.prev_tab()
            
        if self._is_pressed(CONFIG.controls.down, key) and self.ui.get_current_tab() == 2:
            self.ui.next_move()
        elif self._is_pressed(CONFIG.controls.up, key) and self.ui.get_current_tab() == 2:
            self.ui.prev_move()

    def _is_pressed(self, config_key: str, key: int) -> bool:
        return getattr(arcade.key, config_key, None) == key
