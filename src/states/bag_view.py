import arcade
from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from src.core.message_service import MessageService
from data.config import CONFIG
from src.ui.bag_ui import BagUI
from src.systems.bag_system import BagSystem
from src.systems.battle_system import BattleSystem
from src.states.battle_view import BattleView
from src.constants import MAX_VISIBLE_ITEMS
from src.enums.item_category import ItemCategory
from src.states.base_view import GameView


BAG_CATEGORIES = [
    ItemCategory.MEDICINE,
    ItemCategory.POKEBALL,
    ItemCategory.HELD_ITEM,
    ItemCategory.BERRY,
]


class BagView(GameView):
    def __init__(
        self,
        previous_view: arcade.View,
        player_manager: PlayerManager,
        data_loader: DataLoader,
        message_service: MessageService,
        battle_system: BattleSystem | None = None,
    ):
        super().__init__()

        self.player_manager = player_manager
        self.data_loader = data_loader
        self.message_service = message_service

        self.ui = BagUI()
        self.bagSystem = BagSystem(player_manager, data_loader)
        self.battle_system = battle_system
        self.previous_view = previous_view

        self.bag = self.bagSystem.get_items()
        self.current_inventory = self.bag.get(ItemCategory.MEDICINE, [])
        self.bagIndex = 0
        self.currentIndex = 0
        self.topVisibleIndex = 0

        self.ui.setup_invetory()
        self.update_item()

    def on_show_view(self):
        self.ui.manager.enable()

    def on_hide_view(self):
        self.ui.manager.disable()

    def update_item(self):
        self.bag = self.bagSystem.get_items()
        self.current_inventory = self.bag.get(
            BAG_CATEGORIES[self.bagIndex], [])

        for i in range(MAX_VISIBLE_ITEMS):
            inventory_index = self.topVisibleIndex + i
            if inventory_index < len(self.current_inventory):
                item = self.current_inventory[inventory_index]
                name = item.name.upper()
                display = f"{name:<14} x{item.count}" if item.count > 0 else name
                self.ui.itemLabels[i].text = display
            else:
                self.ui.itemLabels[i].text = ""

        if len(self.current_inventory) <= 0:
            self.currentIndex = 0
            self.ui.set_text("There isn't any items.")
            return

        if self.currentIndex >= len(self.current_inventory):
            self.currentIndex = len(self.current_inventory) - 1
            self.topVisibleIndex = min(self.topVisibleIndex, self.currentIndex)

        index = self.currentIndex - self.topVisibleIndex
        self.ui.set_y_of_cursor(index)

        item_data = self.data_loader.get_item(
            self.current_inventory[self.currentIndex].name
        )
        if item_data is not None:
            self.ui.set_text(item_data.description)
        else:
            self.ui.set_text("Unknown item description.")

    def on_key_press(self, symbol: int, modifiers: int):
        if self.is_pressed(CONFIG.controls.up, symbol):
            self._move_selection(-1)
        elif self.is_pressed(CONFIG.controls.down, symbol):
            self._move_selection(1)
        elif self.is_pressed(CONFIG.controls.right, symbol):
            self.bagIndex = (self.bagIndex + 1) % len(BAG_CATEGORIES)
            self.change_bag()
        elif self.is_pressed(CONFIG.controls.left, symbol):
            self.bagIndex = (self.bagIndex - 1) % len(BAG_CATEGORIES)
            self.change_bag()
        elif self.is_pressed(CONFIG.controls.cancel, symbol):
            self.window.show_view(self.previous_view)
        elif self.is_pressed(CONFIG.controls.interact, symbol):
            self._on_interact()

    def _move_selection(self, delta: int):
        new_index = self.currentIndex + delta
        if not (0 <= new_index < len(self.current_inventory)):
            return

        self.currentIndex = new_index
        if delta < 0 and self.currentIndex < self.topVisibleIndex:
            self.topVisibleIndex -= 1
        elif (
            delta > 0 and self.currentIndex >= self.topVisibleIndex + MAX_VISIBLE_ITEMS
        ):
            self.topVisibleIndex += 1
        self.update_item()

    def _on_interact(self):
        if self.bagIndex in (0, 2):
            self._open_item_menu()
        elif (
            self.bagIndex == 1
            and self.battle_system is not None
            and not self.battle_system.is_trainer
        ):
            self._throw_pokeball(self.battle_system)

    def _open_item_menu(self):
        self.overlay(
            "pokemon_menu",
            previous_view=self,
            bag=self.bagSystem,
            item=self.current_inventory[self.currentIndex].name,
            battle_system=self.battle_system,
        )
        self.update_item()

    def _throw_pokeball(self, battle_system: BattleSystem):
        pokeball = self.bagSystem.use_pokeball(
            self.current_inventory[self.currentIndex].name
        )
        if pokeball:
            result = battle_system.attempt_catch(pokeball)
            self.update_item()
            self.window.show_view(self.previous_view)
            if isinstance(self.previous_view, BattleView):
                self.previous_view.start_catch_attempt(result)

    def change_bag(self):
        self.currentIndex = 0

        category = BAG_CATEGORIES[self.bagIndex]
        self.current_inventory = self.bag.get(category, [])
        self.ui.change_bag(category)

        self.ui.setup_invetory()
        self.update_item()

    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        self.ui.draw()
