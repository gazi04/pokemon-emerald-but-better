import arcade
from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from data.config import Config
from src.ui.pokedex_ui import PokedexUi

CONFIG = Config.load()


class PokedexView(arcade.View):
    """Full-screen Pokédex view — shows all known Pokémon with seen/owned status."""

    def __init__(
        self,
        previous_window: arcade.View,
        player_manager: PlayerManager,
        data_loader: DataLoader,
    ):
        super().__init__(background_color=(0, 0, 0))
        self.previous_window = previous_window
        self.player_manager = player_manager
        self.data_loader = data_loader

        all_pokemon = list(data_loader.pokemons.keys())
        owned = {p.name for p in player_manager.get_pokemon_team()}
        seen = set(player_manager.get_seen_pokemon())

        self.ui = PodedexUi(data_loader, all_pokemon, owned, seen)

    def on_show_view(self):
        self.ui._manager.enable()

    def on_hide_view(self):
        self.ui._manager.disable()

    def on_draw(self):
        self.clear()
        self.ui.draw()

    def on_key_press(self, key: int, modifiers: int):
        if self._is_pressed(CONFIG.controls.cancel, key):
            self.window.show_view(self.previous_window)

        elif self._is_pressed(CONFIG.controls.up, key):
            self.ui.move_up()

        elif self._is_pressed(CONFIG.controls.down, key):
            self.ui.move_down()

    def _is_pressed(self, config_key: str, key: int) -> bool:
        return getattr(arcade.key, config_key, None) == key
