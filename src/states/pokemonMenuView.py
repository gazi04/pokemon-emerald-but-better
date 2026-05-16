import arcade
from src.ui.pokemonMenuUi import PokemonMenuUi
from src.core.gameContext import saveManager
from data.config import Config
from src.constants import FONT


CONFIG = Config.load()

class PokemonMenuView(arcade.View):
    def __init__(self, previousView:arcade.View):
        super().__init__()
        
        self.previousView = previousView
        
        arcade.load_font(FONT)
        
        self.team = saveManager.player.pokemon
        self.teamIndex = 0
        self.tooltipIndex = 0
        
        self.isMovingPokemon = False
        self.movingPokemonIndex = 0
        
        self.ui = PokemonMenuUi()
        self.ui.setValues(self.team)
    
    def on_draw(self):
        self.clear()
        self.ui.draw()
        self.ui.drawHpBars(self.team)

    def on_key_press(self, key, modifiers):
        if (self.ui.isTooltipShowing()):
            self.tooltip(key)
            return
        
        if self.isPressed(CONFIG.controls.cancel, key) and not self.isMovingPokemon:
            self.window.show_view(self.previousView)
        elif self.isPressed(CONFIG.controls.cancel, key) and self.isMovingPokemon:
            self.isMovingPokemon = False

        self.handlePokemonSelection(key)

    def handlePokemonSelection(self, key):
        if self.isPressed(CONFIG.controls.interact, key):
            if not self.isMovingPokemon:
                self.ui.showTooltip(self.teamIndex)
            else:
                self.movePokemon(self.teamIndex)
        elif self.isPressed(CONFIG.controls.down, key):
            self.teamIndex += 1
            
            if self.teamIndex == len(self.team):
                self.teamIndex = 0
        elif self.isPressed(CONFIG.controls.up, key):
            self.teamIndex -= 1
            
            if self.teamIndex == -1:
                self.teamIndex = len(self.team) - 1
        
        self.ui.selectPokemon(self.teamIndex)

    def tooltip(self, key):
        if self.isMovingPokemon:
            self.handlePokemonSelection(key)
            return
        
        if self.isPressed(CONFIG.controls.cancel, key):
            self.ui.hideTooltip()
            self.tooltipIndex = 0
        elif self.isPressed(CONFIG.controls.interact, key):
            self.ui.hideTooltip()
            if self.tooltipIndex == 1 and len(self.team) > 1:
                self.isMovingPokemon = True
                self.movingPokemonIndex = self.teamIndex
                print("Start moving pokemon")
            elif self.tooltipIndex == 0:
                pass
        elif self.isPressed(CONFIG.controls.down, key):
            self.tooltipIndex = 1 if self.tooltipIndex == 0 else 0
                
            self.ui.selectTooltipOption(self.tooltipIndex)
        elif self.isPressed(CONFIG.controls.up, key):
            self.tooltipIndex = 0 if self.tooltipIndex == 1 else 1
                
            self.ui.selectTooltipOption(self.tooltipIndex)

    def movePokemon(self, to: int):
        if to == self.movingPokemonIndex:
            self.isMovingPokemon = False
            return
        
        self.team[to], self.team[self.movingPokemonIndex] = self.team[self.movingPokemonIndex], self.team[to]
        
        self.ui.setValues(self.team)
        self.isMovingPokemon = False

    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key