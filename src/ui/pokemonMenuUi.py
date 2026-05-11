import arcade
import arcade.gui

class PokemonMenuUi:
    def __init__(self):
        self.manager = arcade.gui.UIManager()
    
    def draw(self):
        self.manager.draw()