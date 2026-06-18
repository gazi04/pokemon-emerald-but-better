import arcade
from typing import Optional
from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
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
        player_manager: PlayerManager,
        data_loader: DataLoader,
        bag: Optional[BagSystem] = None,
        itemIndex: int = 0,
        battleSystem: Optional[BattleSystem] = None,
        forced_switch: bool = False,
    ):
        super().__init__()

        self.previousView = previousView
        self.bag = bag
        self.battleSystem = battleSystem
        self.itemIndex = itemIndex
        self.forced_switch = forced_switch

        self.data_loader = data_loader
        self.system = PokemonMenuSystem(player_manager)
        self.ui = PokemonMenuUi(data_loader)

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

    def on_key_press(self, symbol: int, modifiers: int):
        if self.ui.isTooltipShowing():
            self._handleTooltipInput(symbol)
        else:
            self._handleMenuInput(symbol)

    def _handleMenuInput(self, key):
        if self._is_pressed(CONFIG.controls.cancel, key):
            if self.forced_switch:
                return  # Can't back out — a replacement must be chosen.
            if self.system.isMovingPokemon:
                self.system.cancelMoving()
            else:
                self.window.show_view(self.previousView)
            return

        if self._is_pressed(CONFIG.controls.interact, key):
            if self.forced_switch:
                self._do_forced_switch()
            elif self.system.isMovingPokemon:
                if not self.battleSystem:
                    self.system.movePokemon(self.system.teamIndex)
                    self.ui.setValues(self.system.team)
            else:
                self.ui.showTooltip(self.system.teamIndex)
        elif self._is_pressed(CONFIG.controls.down, key):
            self.system.moveTeamIndex(1)
        elif self._is_pressed(CONFIG.controls.up, key):
            self.system.moveTeamIndex(-1)

        self.ui.selectPokemon(self.system.teamIndex)

    def _do_forced_switch(self):
        selected = self.system.team[self.system.teamIndex]
        # Can't send out a fainted Pokémon or the one already out.
        if selected.hp <= 0 or self.system.teamIndex == 0:
            return

        self.system.confirmSwitch(self.system.teamIndex)
        self.ui.setValues(self.system.team)
        self.previousView.force_switch()
        self.window.show_view(self.previousView)

    def _handleTooltipInput(self, key):
        if self._is_pressed(CONFIG.controls.cancel, key):
            self.ui.hideTooltip()
            self.system.resetTooltip()
        elif self._is_pressed(CONFIG.controls.interact, key):
            self._tooltipAction()
        elif self._is_pressed(CONFIG.controls.down, key):
            self.system.moveTooltipIndex(1, len(self.ui._tooltipButtons))
            self.ui.selectTooltipOption(self.system.tooltipIndex)
        elif self._is_pressed(CONFIG.controls.up, key):
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
                self._move_pokemon()

        elif index == 0:
            global_bus.publish(
                OverlayViewEvent(
                    target="pokemon_information",
                    payload={
                        "previous_view": self,
                        "pokemon": self.system.team[self.system.teamIndex]
                    },
                )
            )
        
    def _move_pokemon(self):
        if not self.battleSystem:
            self.system.startMoving()
            return
        
        success = self.system.confirmSwitch(self.system.teamIndex)
        if success:
            self.ui.setValues(self.system.team)
            self.previousView.switch_turn()
            self.window.show_view(self.previousView)

    def _is_pressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key
