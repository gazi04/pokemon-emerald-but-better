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
        item_index: int = 0,
        battle_system: Optional[BattleSystem] = None,
        forced_switch: bool = False,
    ):
        super().__init__()

        self.previousView = previousView
        self.bag = bag
        self.battle_system = battle_system
        self.item_index = item_index
        self.forced_switch = forced_switch

        self.data_loader = data_loader
        self.system = PokemonMenuSystem(player_manager)
        self.ui = PokemonMenuUi(data_loader)

        if bag:
            tooltipOptions = ["Use", "Info"]
        elif battle_system:
            tooltipOptions = ["Switch", "Info"]
        else:
            tooltipOptions = ["Move", "Info"]

        self.ui.setup_tooltip(tooltipOptions)
        self.ui.set_values(self.system.team)

    def on_draw(self):
        self.clear()
        self.ui.draw()
        self.ui.draw_hp_bars(self.system.team)

    def on_key_press(self, symbol: int, modifiers: int):
        if self.ui.is_tooltip_showing():
            self._handleTooltipInput(symbol)
        else:
            self._handleMenuInput(symbol)

    def _handleMenuInput(self, key):
        if self._is_pressed(CONFIG.controls.cancel, key):
            if self.forced_switch:
                return  # Can't back out — a replacement must be chosen.
            if self.system.isMovingPokemon:
                self.system.cancel_moving()
            else:
                self.window.show_view(self.previousView)
            return

        if self._is_pressed(CONFIG.controls.interact, key):
            if self.forced_switch:
                self._do_forced_switch()
            elif self.system.isMovingPokemon:
                if not self.battle_system:
                    self.system.move_pokemon(self.system.teamIndex)
                    self.ui.set_values(self.system.team)
            else:
                self.ui.show_tooltip(self.system.teamIndex)
        elif self._is_pressed(CONFIG.controls.down, key):
            self.system.move_team_index(1)
        elif self._is_pressed(CONFIG.controls.up, key):
            self.system.move_team_index(-1)

        self.ui.select_pokemon(self.system.teamIndex)

    def _do_forced_switch(self):
        selected = self.system.team[self.system.teamIndex]
        # Can't send out a fainted Pokémon or the one already out.
        if selected.hp <= 0 or self.system.teamIndex == 0:
            return

        self.system.confirm_switch(self.system.teamIndex)
        self.ui.set_values(self.system.team)
        self.previousView.force_switch()
        self.window.show_view(self.previousView)

    def _handleTooltipInput(self, key):
        if self._is_pressed(CONFIG.controls.cancel, key):
            self.ui.hide_tooltip()
            self.system.reset_tooltip()
        elif self._is_pressed(CONFIG.controls.interact, key):
            self._tooltipAction()
        elif self._is_pressed(CONFIG.controls.down, key):
            self.system.move_tooltip_index(1, len(self.ui._tooltipButtons))
            self.ui.select_tooltip_option(self.system.tooltipIndex)
        elif self._is_pressed(CONFIG.controls.up, key):
            self.system.move_tooltip_index(-1, len(self.ui._tooltipButtons))
            self.ui.select_tooltip_option(self.system.tooltipIndex)

    def _tooltipAction(self):
        index = self.system.tooltipIndex
        self.ui.hide_tooltip()
        self.system.reset_tooltip()

        if index == 1:
            if self.bag and self.battle_system:
                # Use item in battle
                self.bag.use_item(
                    self.item_index,
                    self.system.team[self.system.teamIndex].name,
                )

                # Navigate back to BattleView (still held by previousView chain)
                battleView = self.previousView.previousWindow
                battleView.on_item_used(self.item_index)
                self.window.show_view(battleView)

            elif self.bag:
                # Use item outside battle
                self.bag.use_item(
                    self.item_index,
                    self.system.team[self.system.teamIndex].name,
                )
                self.previousView.update_item()
                self.window.show_view(self.previousView)

            elif len(self.system.team) > 1:
                self._move_pokemon()

        elif index == 0:
            global_bus.publish(
                OverlayViewEvent(
                    target="pokemon_information",
                    payload={
                        "previous_view": self,
                        "pokemon": self.system.team[self.system.teamIndex],
                    },
                )
            )

    def _move_pokemon(self):
        if not self.battle_system:
            self.system.start_moving()
            return

        success = self.system.confirm_switch(self.system.teamIndex)
        if success:
            self.ui.set_values(self.system.team)
            self.previousView.switch_turn()
            self.window.show_view(self.previousView)

    def _is_pressed(self, config_key, key) -> bool:
        return getattr(arcade.key, config_key, None) == key
