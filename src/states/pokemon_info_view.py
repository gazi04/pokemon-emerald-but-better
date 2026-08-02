import arcade
from src.core.data_loader import DataLoader
from src.model.save.player import PlayerPokemon
from src.states.base_view import GameView
from src.ui.pokemon_information_ui import PokemonInformationUI
from data.config import CONFIG
from collections.abc import Callable


class PokemonInfoView(GameView):
    def __init__(
        self,
        previous_view: arcade.View,
        data_loader: DataLoader,
        pokemon: PlayerPokemon | None = None,
        select_move: bool = False,
        on_select_move: Callable[[int], None] | None = None,
    ):
        super().__init__(background_color=(0, 104, 96))
        self.previous_view = previous_view

        if pokemon is None:
            raise ValueError("PokemonInfoView requires a pokemon to display.")
        self.ui = PokemonInformationUI(pokemon, data_loader)

        # "Select move" mode: locked to the moves tab, used to pick which move a
        # PP-restoring item (Ether) targets. `on_select_move(index)` is called
        # with the chosen move and is responsible for navigating onward.
        self.select_move = select_move
        self.on_select_move = on_select_move
        if select_move:
            self.ui.show_moves_tab()

    def on_key_press(self, symbol: int, modifiers: int):
        if self.is_pressed(CONFIG.controls.cancel, symbol):
            self.window.show_view(self.previous_view)
            return

        if self.select_move:
            self._handle_move_select(symbol)
            return

        if self.is_pressed(CONFIG.controls.right, symbol):
            self.ui.next_tab()
        elif self.is_pressed(CONFIG.controls.left, symbol):
            self.ui.prev_tab()
        elif (
            self.is_pressed(CONFIG.controls.down, symbol)
            and self.ui.get_current_tab() == 2
        ):
            self.ui.next_move()
        elif (
            self.is_pressed(CONFIG.controls.up, symbol)
            and self.ui.get_current_tab() == 2
        ):
            self.ui.prev_move()

    def _handle_move_select(self, key: int):
        if self.is_pressed(CONFIG.controls.down, key):
            self.ui.next_move()
        elif self.is_pressed(CONFIG.controls.up, key):
            self.ui.prev_move()
        elif self.is_pressed(CONFIG.controls.interact, key) and self.on_select_move:
            self.on_select_move(self.ui.current_move())
