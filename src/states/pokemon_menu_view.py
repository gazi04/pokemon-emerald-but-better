import arcade
from typing import Optional
from src.core.data_loader import DataLoader
from src.core.save_manager import SaveManager
from src.ui.pokemon_menu_ui import PokemonMenuUi
from src.systems.bag_system import BagSystem
from src.systems.pokemon_menu_system import PokemonMenuSystem
from src.systems.battle_system import BattleSystem
from data.config import Config
from src.core.event_bus import global_bus
from src.core.events import OverlayViewEvent

CONFIG = Config.load()


class PokemonMenuView(arcade.View):
    def __init__(
        self,
        previousView: arcade.View,
        save_manager: SaveManager,
        data_loader: DataLoader,
        bag: Optional[BagSystem] = None,
        itemIndex: int = 0,
        battleSystem: Optional[BattleSystem] = None,
    ):
        super().__init__()

        self.previousView = previousView
        self.bag = bag
        self.battleSystem = battleSystem
        self.itemIndex = itemIndex

        self.data_loader = data_loader
        self.system = PokemonMenuSystem(save_manager)
        self.ui = PokemonMenuUi(data_loader)

        tooltipOptions = ["Use", "Info"] if bag else ["Move", "Info"]
        self.ui.setupTooltip(tooltipOptions)
        self.ui.setValues(self.system.team)

    def on_draw(self):
        self.clear()
        self.ui.draw()
        self.ui.drawHpBars(self.system.team)

    def on_key_press(self, symbol: int, modifiers: int):
        if self.ui.isTooltipShowing():
            self._handleTooltipInput(symbol)
        else:
            self._handleMenuInput(symbol)

    def _handleMenuInput(self, key):
        if self.isPressed(CONFIG.controls.cancel, key):
            if self.system.isMovingPokemon:
                self.system.cancelMoving()
            else:
                self.window.show_view(self.previousView)
            return

        if self.isPressed(CONFIG.controls.interact, key):
            if self.system.isMovingPokemon:
                self.system.movePokemon(self.system.teamIndex)
                self.ui.setValues(self.system.team)
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
                # Use item in battle
                self.bag.useItem(
                    self.itemIndex,
                    self.system.team[self.system.teamIndex].name,
                )
                self.battleSystem.turnUseItem(self.itemIndex)

                # Navigate back to BattleView (still held by previousView chain)
                battleView = self.previousView.previousWindow
                battleView.onItemUsed(self.itemIndex)
                self.window.show_view(battleView)

            elif self.bag:
                # Use item outside battle
                self.bag.useItem(
                    self.itemIndex,
                    self.system.team[self.system.teamIndex].name,
                )
                self.previousView.updateItem()
                self.window.show_view(self.previousView)

            elif len(self.system.team) > 1:
                self.system.startMoving()

        elif index == 0:
            global_bus.publish(
                OverlayViewEvent(
                    target="pokemon_informacion",
                    payload={
                        "previous_view": self,
                        "pokemon": self.system.team[self.system.teamIndex],
                        "data_loader": self.data_loader
                    },
                )
            )

    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key
