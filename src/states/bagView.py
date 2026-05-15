import arcade
from data.config import Config
from src.core.gameContext import saveManager, dataLoader
from src.ui.bagUi import BagUI
from src.core.bagSystem import BagSystem
from src.constants import MAX_VISIBLE_ITEMS

CONFIG = Config.load()


class BagView(arcade.View):
    def __init__(self, previousWindow: arcade.View):
        super().__init__()

        self.bagUi = BagUI()
        self.bagSystem = BagSystem()

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
                if item.count > 0:
                    display = f"{name:<14} x{item.count}"
                else:
                    display = name

                self.bagUi.itemLabels[i].text = display
            else:
                self.bagUi.itemLabels[i].text = ""

        if len(self.inventory) <= 0:
            self.currentIndex = 0
            self.bagUi.setText("There isnt any items.")
            return

        index = self.currentIndex - self.topVisibleIndex
        self.bagUi.setYOfCursor(index)
        self.bagUi.setText(dataLoader.getItem(self.inventory[self.currentIndex].name).description)

    def on_key_press(self, key, modifiers):
        if self.isPressed(CONFIG.controls.up, key):
            if self.currentIndex > 0:
                self.currentIndex -= 1

                if self.currentIndex < self.topVisibleIndex:
                    self.topVisibleIndex -= 1

                self.updateItem()
        elif self.isPressed(CONFIG.controls.down, key):
            if self.currentIndex < len(self.inventory) - 1:
                self.currentIndex += 1

                if self.currentIndex >= self.topVisibleIndex + MAX_VISIBLE_ITEMS:
                    self.topVisibleIndex += 1

                self.updateItem()
        elif self.isPressed(CONFIG.controls.right, key):
            self.bagIndex = 1 if self.bagIndex == 0 else 0

            self.changeBag()
        elif self.isPressed(CONFIG.controls.left, key):
            self.bagIndex = 0 if self.bagIndex == 1 else 1

            self.changeBag()
        elif self.isPressed(CONFIG.controls.cancel, key):
            self.window.show_view(self.previousWindow)
        elif self.isPressed(CONFIG.controls.interact, key) and self.bagIndex == 0:
            self.bagSystem.useItem(self.currentIndex)
            self.updateItem()
            
    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key

    def changeBag(self):
        self.currentIndex = 0
        if self.bagIndex == 0:
            self.inventory = self.bagSystem.getItems()
            self.bagUi.changeBag("items")

            self.bagUi.setupInvetory()
            self.updateItem()
        else:
            self.inventory = self.bagSystem.getPokeballs()
            self.bagUi.changeBag("pokeball")

            self.bagUi.setupInvetory()
            self.updateItem()

    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        self.bagUi.draw()
