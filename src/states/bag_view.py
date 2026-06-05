import arcade
from typing import Optional
from src.core.data_loader import DataLoader
from src.core.save_manager import SaveManager
from data.config import Config
from src.ui.bag_ui import BagUI
from src.systems.bag_system import BagSystem
from src.systems.battle_system import BattleSystem
from src.constants import MAX_VISIBLE_ITEMS
from src.core.event_bus import global_bus
from src.core.events import OverlayViewEvent

CONFIG = Config.load()


class BagView(arcade.View):
    def __init__(
        self,
        previousWindow: arcade.View,
        save_manager: SaveManager,
        data_loader: DataLoader,
        battleSystem: Optional[BattleSystem] = None,
    ):
        super().__init__()

        self.save_manager = save_manager
        self.data_loader = data_loader

        self.bagUi = BagUI()
        self.bagSystem = BagSystem(save_manager, data_loader)
        self.battleSystem = battleSystem
        self.previousWindow = previousWindow

        self.inventory = self.bagSystem.getItems()
        self.bagIndex = 0
        self.currentIndex = 0
        self.topVisibleIndex = 0

        self.bagUi.setupInvetory()
        self.updateItem()

    def updateItem(self):
        for i in range(MAX_VISIBLE_ITEMS):
            inventory_index = self.topVisibleIndex + i
            if inventory_index < len(self.inventory):
                item = self.inventory[inventory_index]
                name = item.name.upper()
                display = f"{name:<14} x{item.count}" if item.count > 0 else name
                self.bagUi.itemLabels[i].text = display
            else:
                self.bagUi.itemLabels[i].text = ""

        if len(self.inventory) <= 0:
            self.currentIndex = 0
            self.bagUi.setText("There isn't any items.")
            return

        index = self.currentIndex - self.topVisibleIndex
        self.bagUi.setYOfCursor(index)

        item_data = self.data_loader.getItem(self.inventory[self.currentIndex].name)
        if item_data is not None:
            self.bagUi.setText(item_data.description)
        else:
            self.bagUi.setText("Unknown item description.")

    def on_key_press(self, symbol: int, modifiers: int):
        if self.isPressed(CONFIG.controls.up, symbol):
            if self.currentIndex > 0:
                self.currentIndex -= 1
                if self.currentIndex < self.topVisibleIndex:
                    self.topVisibleIndex -= 1
                self.updateItem()

        elif self.isPressed(CONFIG.controls.down, symbol):
            if self.currentIndex < len(self.inventory) - 1:
                self.currentIndex += 1
                if self.currentIndex >= self.topVisibleIndex + MAX_VISIBLE_ITEMS:
                    self.topVisibleIndex += 1
                self.updateItem()

        elif self.isPressed(CONFIG.controls.right, symbol):
            self.bagIndex = 1 if self.bagIndex == 0 else 0
            self.changeBag()

        elif self.isPressed(CONFIG.controls.left, symbol):
            self.bagIndex = 0 if self.bagIndex == 1 else 1
            self.changeBag()

        elif self.isPressed(CONFIG.controls.cancel, symbol):
            self.window.show_view(self.previousWindow)

        elif self.isPressed(CONFIG.controls.interact, symbol) and self.bagIndex == 0:
            global_bus.publish(
                OverlayViewEvent(
                    target="pokemon_menu",
                    payload={
                        "previous_view": self,
                        "bag": self.bagSystem,
                        "item_index": self.currentIndex,
                        "battle_system": self.battleSystem,
                        "save_manager": self.save_manager,
                        "data_loader": self.data_loader,
                    },
                )
            )
            self.updateItem()
        elif self.isPressed(CONFIG.controls.interact, symbol) and self.bagIndex == 1 and self.battleSystem:
            pokeball = self.bagSystem.usePokeball(self.currentIndex)
            if pokeball:
                result = self.battleSystem.attempt_catch(pokeball)
                self.updateItem()
                self.window.show_view(self.previousWindow)
                if hasattr(self.previousWindow, "startCatchAttempt"):
                    self.previousWindow.startCatchAttempt(result)

    def isPressed(self, configKey, symbol) -> bool:
        return getattr(arcade.key, configKey, None) == symbol

    def changeBag(self):
        self.currentIndex = 0
        if self.bagIndex == 0:
            self.inventory = self.bagSystem.getItems()
            self.bagUi.changeBag("items")
        else:
            self.inventory = self.bagSystem.getPokeballs()
            self.bagUi.changeBag("pokeball")
        self.bagUi.setupInvetory()
        self.updateItem()

    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        self.bagUi.draw()
