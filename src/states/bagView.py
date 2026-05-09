import arcade
from data.config import Config
from src.core.gameContext import saveManager,dataLoader
from src.ui.bagUi import BagUI

CONFIG = Config.load()

class BagView(arcade.View):
    def __init__(self, previousWindow):
        super().__init__()

        self.bagUi = BagUI()

        self.previousWindow = previousWindow

        self.items = saveManager.player.items
        self.pokeball = saveManager.player.pokeballs

        self.inventory = self.items

        self.bagIndex = 0

        self.maxVisibleItems = 10
        self.currentIndex = 0
        self.topVisibleIndex = 0

        self.bagUi.setupInvetory(self.maxVisibleItems)
        self.updateItem()

    def updateItem(self):
        for i in range(self.maxVisibleItems):
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

        index = self.currentIndex - self.topVisibleIndex
        self.bagUi.setYOfCursor(index)
        self.bagUi.dialog.text = dataLoader.getItem(self.inventory[self.currentIndex].name).description

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

                if self.currentIndex >= self.topVisibleIndex + self.maxVisibleItems:
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
            
    def isPressed(self, configKey, key):
        return getattr(arcade.key, configKey, None) == key

    def changeBag(self):
        if self.bagIndex == 0:
            self.inventory = self.items
            self.bagUi.changeBag("items")
            
            self.bagUi.setupInvetory(self.maxVisibleItems)
            self.updateItem()
        else:
            self.inventory = self.pokeball
            self.bagUi.changeBag("pokeball")
            
            self.bagUi.setupInvetory(self.maxVisibleItems)
            self.updateItem()

    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        self.bagUi.draw()
