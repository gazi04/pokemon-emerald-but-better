import arcade

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

sys.path.append(parent_dir)

from ui.pokemonMenuUi import PokemonMenuUi

class PokemonMenuView(arcade.View):
    def __init__(self):
        super().__init__()
        
        self.ui = PokemonMenuUi()
        
    def on_draw(self):
        self.clear()
        self.ui.draw()

if __name__ == "__main__":
    window = arcade.Window(
        width=800,
        height=600,
    )

    start_view = PokemonMenuView()
    window.show_view(start_view)
    arcade.run()
        