import arcade
from src.ui.pokemonMenuUi import PokemonMenuUi
from src.core.bagSystem import BagSystem
from src.core.gameContext import saveManager
from data.config import Config
from src.constants import FONT


CONFIG = Config.load()

class PokemonMenuView(arcade.View):
    def __init__(self, previousView:arcade.View, bag:BagSystem = None, itemIndex:int = 0):
        super().__init__()
        
        self.previousView = previousView
        self.bag = bag
        self.itemIndex = itemIndex
        
        arcade.load_font(FONT)
        
        self.team = saveManager.player.pokemon
        self.teamIndex = 0
        self.tooltipIndex = 0
        
        self.isMovingPokemon = False
        self.movingPokemonIndex = 0
        
        self.ui = PokemonMenuUi()
        if not self.bag:
            self.ui.setupTooltip(["Move", "Info"])
        else:
            self.ui.setupTooltip(["Use", "Info"])
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
            self.tooltipAction()
        elif self.isPressed(CONFIG.controls.down, key):
            self.tooltipIndex += 1
            if self.tooltipIndex == len(self.ui._tooltipButtons):
                self.tooltipIndex = 0
                
            self.ui.selectTooltipOption(self.tooltipIndex)
        elif self.isPressed(CONFIG.controls.up, key):
            self.tooltipIndex -= 1
            if self.tooltipIndex == -1:
                self.tooltipIndex = len(self.ui._tooltipButtons) - 1
                
            self.ui.selectTooltipOption(self.tooltipIndex)

    def tooltipAction(self):
        self.ui.hideTooltip()
        print(self.tooltipIndex)
        
        if self.tooltipIndex == 0:
            return
        
        if (self.bag and self.itemIndex is not None) and self.tooltipIndex == 1:
            self.bag.useItem(self.itemIndex, self.team[self.teamIndex].name)
            self.previousView.updateItem()
            self.window.show_view(self.previousView)
            return
        
        if self.tooltipIndex == 1 and len(self.team) > 1:
            self.isMovingPokemon = True
            self.movingPokemonIndex = self.teamIndex
            self.tooltipIndex = 0
            
    def movePokemon(self, to: int):
        if to == self.movingPokemonIndex:
            self.isMovingPokemon = False
            return
        
        self.team[to], self.team[self.movingPokemonIndex] = self.team[self.movingPokemonIndex], self.team[to]
        
        self.ui.setValues(self.team)
        self.isMovingPokemon = False

    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key