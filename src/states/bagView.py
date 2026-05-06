import arcade
import arcade.gui
from src.util import getPlayerItems, getPlayerPokeball
from data.config import Config
from src.core.gameContext import saveManager,dataLoader

CONFIG = Config.load()

class BagView(arcade.View):
    def __init__(self, previousWindow):
        super().__init__()

        self.previousWindow = previousWindow

        self.manager = arcade.gui.UIManager()
        self.manager._pixelated = True

        tilemap = arcade.load_tilemap("assets/ui/bagUiDesign.tmx")
        uiLayer = tilemap.get_tilemap_layer("ui")

        for obj in uiLayer.tiled_objects:
            w = obj.size.width
            h = obj.size.height

            x = obj.coordinates.x
            y = 600 - obj.coordinates.y

            if obj.name == "background":
                self.manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture(
                            "assets/ui/sprites/bagUi.png"),
                        width=w,
                        height=h,
                        x=x,
                        y=y
                    )
                )
            elif "Arrow" in obj.name:
                self.manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture(
                            f"assets/ui/sprites/{obj.name}.png"),
                        width=w,
                        height=h,
                        x=x,
                        y=y
                    )
                )
            elif obj.name == "section":
                self.sectionText = arcade.gui.UILabel(
                    "ITEMS",
                    x=x,
                    y=y - h,
                    width=w,
                    height=h,
                    text_color=arcade.color.BLACK,
                    font_name="Pokemon Emerald",
                    font_size=25,
                    align="center"
                )
                self.manager.add(self.sectionText)
            elif obj.name == "bag":
                self.bag = arcade.gui.UIImage(
                    texture=arcade.load_texture(
                        "assets/ui/sprites/bagItem.png"),
                    width=w,
                    height=h,
                    x=x,
                    y=y
                )
                self.manager.add(self.bag)
            elif obj.name == "text":
                self.dialog = arcade.gui.UILabel(
                    "",
                    x=x,
                    y=y - h,
                    width=w,
                    height=h,
                    text_color=arcade.color.BLACK,
                    font_name="Pokemon Emerald",
                    font_size=30,
                    multiline=True
                )
                self.manager.add(self.dialog)

        self.items = saveManager.player.items
        self.pokeball = saveManager.player.pokeballs

        self.inventory = self.items

        self.bagIndex = 0

        self.maxVisibleItems = 10
        self.currentIndex = 0
        self.topVisibleIndex = 0

        self.itemLabels = []

        self.startX = 420
        self.startY = 500
        self.spacing = 40

        self.cursorLabel = arcade.Text(
            text="▶",
            x=self.startX - 30,
            y=self.startY,
            width=30,
            height=self.spacing,
            color=arcade.color.RED,
            font_name="Pokemon Emerald",
            font_size=20
        )

        self.setupInvetory()

    def setupInvetory(self):
        for item in self.itemLabels:
            self.manager.remove(item)

        self.currentIndex = 0
        self.itemLabels.clear()

        for i in range(self.maxVisibleItems):
            label = arcade.gui.UILabel(
                text="",
                x=self.startX,
                y=self.startY - (i * self.spacing),
                width=250,
                height=self.spacing,
                text_color=arcade.color.BLACK,
                font_name="Pokemon Emerald",
                font_size=30
            )
            self.itemLabels.append(label)
            self.manager.add(label)

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

                self.itemLabels[i].text = display
            else:
                self.itemLabels[i].text = ""

        index = self.currentIndex - self.topVisibleIndex
        self.cursorLabel.y = self.startY - \
            (index * self.spacing) + (self.spacing / 3)
        self.dialog.text = dataLoader.getItem(self.inventory[self.currentIndex].name).description

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
            self.sectionText.text = "ITEMS"
            self.inventory = self.items
            self.bag.texture = arcade.load_texture(
                "assets/ui/sprites/bagItem.png")
            self.setupInvetory()
        else:
            self.sectionText.text = "POKEBALL"
            self.inventory = self.pokeball
            self.bag.texture = arcade.load_texture(
                "assets/ui/sprites/bagPokeball.png")
            self.setupInvetory()

    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        self.manager.draw()
        self.cursorLabel.draw()
