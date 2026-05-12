import arcade
from src.ui.pokemonMenuUi import PokemonMenuUi
from src.core.gameContext import saveManager
from data.config import Config
from src.constants import FONT


CONFIG = Config.load()

class PokemonMenuView(arcade.View):
    def __init__(self):
        super().__init__()
        
        arcade.load_font(FONT)
        
        self.team = saveManager.player.pokemon
        self.index = 0
        
        self.ui = PokemonMenuUi()
        self.ui.setValues(self.team)
    
    def on_draw(self):
        self.clear()
        self.ui.draw()
        self.ui.drawHpBars(self.team)

    def on_key_press(self, key, modifiers):
        if self.isPressed(CONFIG.controls.down, key):
            self.index += 1
            
            if self.index == len(self.team):
                self.index = 0
                
            self.ui.selectPokemon(self.index)
        elif self.isPressed(CONFIG.controls.up, key):
            self.index -= 1
            
            if self.index == -1:
                self.index = len(self.team) - 1
                
            self.ui.selectPokemon(self.index)

    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key