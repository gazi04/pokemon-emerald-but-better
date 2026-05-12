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
        self.teamIndex = 0
        
        self.ui = PokemonMenuUi()
        self.ui.setValues(self.team)
    
    def on_draw(self):
        self.clear()
        self.ui.draw()
        self.ui.drawHpBars(self.team)

    def on_key_press(self, key, modifiers):
        if self.isPressed(CONFIG.controls.down, key):
            self.teamIndex += 1
            
            if self.teamIndex == len(self.team):
                self.teamIndex = 0
                
            self.ui.selectPokemon(self.teamIndex)
        elif self.isPressed(CONFIG.controls.up, key):
            self.teamIndex -= 1
            
            if self.teamIndex == -1:
                self.teamIndex = len(self.team) - 1
                
            self.ui.selectPokemon(self.teamIndex)
        elif self.isPressed(CONFIG.controls.interact, key):
            self.ui.showTooltip(self.teamIndex)

    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key