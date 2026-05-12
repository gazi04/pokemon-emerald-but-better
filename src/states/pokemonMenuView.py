import arcade
from src.ui.pokemonMenuUi import PokemonMenuUi
from src.core.gameContext import saveManager

class PokemonMenuView(arcade.View):
    def __init__(self):
        super().__init__()
        
        self.ui = PokemonMenuUi()
        self.ui.setValues(saveManager.player.pokemon)
    
    def on_draw(self):
        self.clear()
        self.ui.draw()
        self.ui.drawHpBars(saveManager.player.pokemon)
