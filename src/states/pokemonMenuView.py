import arcade
from src.ui.pokemonMenuUi import PokemonMenuUi
from src.core.bagSystem import BagSystem
from src.core.pokemonMenuSystem import PokemonMenuSystem
from src.core.battleSystem import BattleSystem
from data.config import Config
from src.constants import FONT

CONFIG = Config.load()


class PokemonMenuView(arcade.View):
    def __init__(self, previousView:arcade.View, bag:BagSystem = None, itemIndex:int = 0, battleSystem: BattleSystem = None):
        super().__init__()

        self.previousView = previousView
        self.bag = bag
        self.battleSystem = battleSystem
        self.itemIndex = itemIndex
        
        self.system = PokemonMenuSystem()
        self.ui = PokemonMenuUi()
        
        if bag:
            tooltipOptions = ["Use", "Info"]
        elif battleSystem:
            tooltipOptions = ["Switch", "Info"]
        else:
            tooltipOptions = ["Move", "Info"]
            
        self.ui.setupTooltip(tooltipOptions)
        self.ui.setValues(self.system.team)
    
    def on_draw(self):
        self.clear()
        self.ui.draw()
        self.ui.drawHpBars(self.system.team)

    def on_key_press(self, key, modifiers):
        if self.ui.isTooltipShowing():
            self._handleTooltipInput(key)
        else:
            self._handleMenuInput(key)

    def _handleMenuInput(self, key):
        if self.isPressed(CONFIG.controls.cancel, key):
            if self.system.isMovingPokemon:
                self.system.cancelMoving()
            else:
                self.window.show_view(self.previousView)
            return

        if self.isPressed(CONFIG.controls.interact, key):
            if self.system.isMovingPokemon:
                if not self.battleSystem:
                    self.system.movePokemon(self.system.teamIndex)
                    self.ui.setValues(self.system.team)
                else:
                    success = self.system.confirmSwitch(self.system.teamIndex)
                    if success:
                        self.ui.setValues(self.system.team)
                        self.previousView.switchTurn()
                        self.window.show_view(self.previousView)
            else:
                self.ui.showTooltip(self.system.teamIndex)
        elif self.isPressed(CONFIG.controls.down, key):
            self.system.moveTeamIndex(1)
        elif self.isPressed(CONFIG.controls.up, key):
            self.system.moveTeamIndex(-1)

        self.ui.selectPokemon(self.system.teamIndex)

    def _handleTooltipInput(self, key):
        if self.isPressed(CONFIG.controls.cancel, key):
            self.ui.hideTooltip()
            self.system.resetTooltip()
        elif self.isPressed(CONFIG.controls.interact, key):
            self._tooltipAction()
        elif self.isPressed(CONFIG.controls.down, key):
            self.system.moveTooltipIndex(1, len(self.ui._tooltipButtons))
            self.ui.selectTooltipOption(self.system.tooltipIndex)
        elif self.isPressed(CONFIG.controls.up, key):
            self.system.moveTooltipIndex(-1, len(self.ui._tooltipButtons))
            self.ui.selectTooltipOption(self.system.tooltipIndex)

    def _tooltipAction(self):
        index = self.system.tooltipIndex
        self.ui.hideTooltip()
        self.system.resetTooltip()

        if index == 1: 
            if self.bag and self.battleSystem:
                self.bag.useItem(self.itemIndex, self.system.team[self.system.teamIndex].name)
                self.battleSystem.turnUseItem(self.itemIndex)
                
                battleView = self.previousView.previousWindow 
                battleView.onItemUsed(self.itemIndex)
                self.window.show_view(battleView)
            elif self.bag:
                self.bag.useItem(self.itemIndex, self.system.team[self.system.teamIndex].name)
                self.previousView.updateItem()
                self.window.show_view(self.previousView)
            elif len(self.system.team) > 1:
                self.system.startMoving()
        elif index == 0:
            pass

    
    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key
