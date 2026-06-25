import arcade
from typing import Optional
from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from src.core.message_service import MessageService
from data.config import Config
from src.ui.bag_ui import BagUI
from src.systems.bag_system import BagSystem
from src.systems.battle_system import BattleSystem
from src.constants import MAX_VISIBLE_ITEMS
from src.states.base_view import GameView

CONFIG = Config.load()


class BagView(GameView):
    def __init__(
        self,
        previousWindow: arcade.View,
        player_manager: PlayerManager,
        data_loader: DataLoader,
        message_service: MessageService,
        battle_system: Optional[BattleSystem] = None,
    ):
        super().__init__()

        self.player_manager = player_manager
        self.data_loader = data_loader
        self.message_service = message_service

        self.ui = BagUI()
        self.bagSystem = BagSystem(player_manager, data_loader)
        self.battle_system = battle_system
        self.previousWindow = previousWindow

        self.inventory = self.bagSystem.get_items()
        self.bagIndex = 0
        self.currentIndex = 0
        self.topVisibleIndex = 0

        self.ui.setup_invetory()
        self.update_item()

    def update_item(self):
        for i in range(MAX_VISIBLE_ITEMS):
            inventory_index = self.topVisibleIndex + i
            if inventory_index < len(self.inventory):
                item = self.inventory[inventory_index]
                name = item.name.upper()
                display = f"{name:<14} x{item.count}" if item.count > 0 else name
                self.ui.itemLabels[i].text = display
            else:
                self.ui.itemLabels[i].text = ""

        if len(self.inventory) <= 0:
            self.currentIndex = 0
            self.ui.set_text("There isn't any items.")
            return

        index = self.currentIndex - self.topVisibleIndex
        self.ui.set_y_of_cursor(index)

        item_data = self.data_loader.get_item(self.inventory[self.currentIndex].name)
        if item_data is not None:
            self.ui.set_text(item_data.description)
        else:
            self.ui.set_text("Unknown item description.")

    def on_key_press(self, symbol: int, modifiers: int):
        if self.is_pressed(CONFIG.controls.up, symbol):
            if self.currentIndex > 0:
                self.currentIndex -= 1
                if self.currentIndex < self.topVisibleIndex:
                    self.topVisibleIndex -= 1
                self.update_item()

        elif self.is_pressed(CONFIG.controls.down, symbol):
            if self.currentIndex < len(self.inventory) - 1:
                self.currentIndex += 1
                if self.currentIndex >= self.topVisibleIndex + MAX_VISIBLE_ITEMS:
                    self.topVisibleIndex += 1
                self.update_item()

        elif self.is_pressed(CONFIG.controls.right, symbol):
            self.bagIndex = 1 if self.bagIndex == 0 else 0
            self.change_bag()

        elif self.is_pressed(CONFIG.controls.left, symbol):
            self.bagIndex = 0 if self.bagIndex == 1 else 1
            self.change_bag()

        elif self.is_pressed(CONFIG.controls.cancel, symbol):
            self.window.show_view(self.previousWindow)

        elif self.is_pressed(CONFIG.controls.interact, symbol) and self.bagIndex == 0:
            self.overlay(
                "pokemon_menu",
                previous_view=self,
                bag=self.bagSystem,
                item_index=self.currentIndex,
                battle_system=self.battle_system,
            )
            self.update_item()
        elif (
            self.is_pressed(CONFIG.controls.interact, symbol)
            and self.bagIndex == 1
            and self.battle_system
            and not self.battle_system.is_trainer
        ):
            pokemon_team = self.battle_system.player_manager.player.pokemon
            if len(pokemon_team) >= 6:
                self.window.show_view(
                    self.previousWindow
                )  # battle re-registers its box
                if hasattr(self.previousWindow, "show_messages"):
                    self.previousWindow.show_messages(
                        ["Your party is full!", "You can't catch any more Pokémon."]
                    )
                return

            pokeball = self.bagSystem.use_pokeball(self.currentIndex)
            if pokeball:
                result = self.battle_system.attempt_catch(pokeball)
                self.update_item()
                self.window.show_view(self.previousWindow)
                if hasattr(self.previousWindow, "start_catch_attempt"):
                    self.previousWindow.start_catch_attempt(result)

    def change_bag(self):
        self.currentIndex = 0
        if self.bagIndex == 0:
            self.inventory = self.bagSystem.get_items()
            self.ui.change_bag("items")
        else:
            self.inventory = self.bagSystem.get_pokeballs()
            self.ui.change_bag("pokeball")
        self.ui.setup_invetory()
        self.update_item()

    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        self.ui.draw()
