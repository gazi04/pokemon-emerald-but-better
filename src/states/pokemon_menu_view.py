import arcade
from typing import Optional
from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from src.ui.pokemon_menu_ui import PokemonMenuUi
from src.systems.bag_system import BagSystem
from src.systems.pokemon_menu_system import PokemonMenuSystem
from src.systems.battle_system import BattleSystem
from data.config import Config
from src.states.base_view import GameView

CONFIG = Config.load()


class PokemonMenuView(GameView):
    def __init__(
        self,
        previousView: arcade.View,
        player_manager: PlayerManager,
        data_loader: DataLoader,
        bag: Optional[BagSystem] = None,
        item: str = "",
        battle_system: Optional[BattleSystem] = None,
        forced_switch: bool = False,
    ):
        super().__init__()

        self.previousView = previousView
        self.bag = bag
        self.battle_system = battle_system
        self.item = item
        self.forced_switch = forced_switch

        self.data_loader = data_loader
        self.player_manager = player_manager
        self.system = PokemonMenuSystem(player_manager)
        self.ui = PokemonMenuUi(data_loader)

        if bag:
            tooltip_options = ["Give it", "Use", "Info"]
        elif battle_system:
            tooltip_options = ["Switch", "Info"]
        else:
            tooltip_options = ["Move", "Info"]

        self.ui.setup_tooltip(tooltip_options)
        self.ui.set_values(self.system.team)

    def on_draw(self):
        self.clear()
        self.ui.draw()
        self.ui.draw_hp_bars(self.system.team)

    def on_key_press(self, symbol: int, modifiers: int):
        if self.ui.is_tooltip_showing():
            self._handle_tooltip_input(symbol)
        else:
            self._handle_menu_input(symbol)

    def _handle_menu_input(self, key):
        if self.is_pressed(CONFIG.controls.cancel, key):
            if self.forced_switch:
                return  # Can't back out — a replacement must be chosen.
            if self.system.is_moving_pokemon:
                self.system.cancel_moving()
            else:
                self.window.show_view(self.previousView)
            return

        if self.is_pressed(CONFIG.controls.interact, key):
            if self.forced_switch:
                self._do_forced_switch()
            elif self.system.is_moving_pokemon:
                if not self.battle_system:
                    self.system.move_pokemon(self.system.team_index)
                    self.ui.set_values(self.system.team)
            else:
                self.ui.show_tooltip(self.system.team_index)
        elif self.is_pressed(CONFIG.controls.down, key):
            self.system.move_team_index(1)
        elif self.is_pressed(CONFIG.controls.up, key):
            self.system.move_team_index(-1)

        self.ui.select_pokemon(self.system.team_index)

    def _do_forced_switch(self):
        selected = self.system.team[self.system.team_index]
        # Can't send out a fainted Pokémon or the one already out.
        if selected.hp <= 0 or self.system.team_index == 0:
            return

        self.system.confirm_switch(self.system.team_index)
        self.ui.set_values(self.system.team)
        self.previousView.force_switch()
        self.window.show_view(self.previousView)

    def _handle_tooltip_input(self, key):
        if self.is_pressed(CONFIG.controls.cancel, key):
            self.ui.hide_tooltip()
            self.system.reset_tooltip()
        elif self.is_pressed(CONFIG.controls.interact, key):
            self._tooltip_action()
        elif self.is_pressed(CONFIG.controls.down, key):
            self.system.move_tooltip_index(1, len(self.ui._tooltip_buttons))
            self.ui.select_tooltip_option(self.system.tooltip_index)
        elif self.is_pressed(CONFIG.controls.up, key):
            self.system.move_tooltip_index(-1, len(self.ui._tooltip_buttons))
            self.ui.select_tooltip_option(self.system.tooltip_index)

    def _tooltip_action(self):
        index = self.system.tooltip_index
        self.ui.hide_tooltip()
        self.system.reset_tooltip()

        if index == 2:
            if self.bag:
                self._get_current_pokemon().held_item = self.item

                self.window.show_view(self.previousView)

        elif index == 1:
            if self.bag:
                # PP items (Ether) need a move chosen first — open the moves tab
                # as a picker; the callback applies the item to that move.
                if self.bag.is_pp_item(self.item):
                    self.overlay(
                        "pokemon_information",
                        previous_view=self,
                        pokemon=self._get_current_pokemon(),
                        select_move=True,
                        on_select_move=self._use_item,
                    )
                else:
                    self._use_item()
            elif len(self.system.team) > 1:
                self._move_pokemon()

        elif index == 0:
            self.overlay(
                "pokemon_information",
                previous_view=self,
                pokemon=self._get_current_pokemon(),
            )

    def _use_item(self, move_index: int | None = None):
        """Apply the selected bag item to the current pokemon. `move_index` is
        the chosen move for PP items (None for others). Also the on_select_move
        callback for the move picker."""
        if self.bag is None:
            raise RuntimeError("_use_item requires the view to be opened with a bag.")
        pokemon_name = self._get_current_pokemon().name

        if self.battle_system:
            # Sync live battle HP/status to the save so the item works on
            # current values, apply, then let the battle pull it back.
            self.battle_system.sync_active_to_save()
            self.bag.use_item(self.item, pokemon_name, move_index)
            battle_view = self.previousView.previousWindow
            battle_view.on_item_used(self.item)
            self.window.show_view(battle_view)
        else:
            self.bag.use_item(self.item, pokemon_name, move_index)
            self.previousView.update_item()
            self.window.show_view(self.previousView)

    def _get_current_pokemon(self):
        return self.system.team[self.system.team_index]

    def _move_pokemon(self):
        if not self.battle_system:
            self.system.start_moving()
            return

        success = self.system.confirm_switch(self.system.team_index)
        if success:
            self.ui.set_values(self.system.team)
            self.previousView.switch_turn()
            self.window.show_view(self.previousView)
