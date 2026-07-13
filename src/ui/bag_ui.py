import arcade
import arcade.gui
from src.constants import BAG_UI, MAX_VISIBLE_ITEMS


class BagUI:
    def __init__(self):
        self.manager = arcade.gui.UIManager()
        self.manager._pixelated = True

        tilemap = arcade.load_tilemap(BAG_UI)
        ui_layer = tilemap.get_tilemap_layer("ui")

        for obj in ui_layer.tiled_objects:
            w = obj.size.width
            h = obj.size.height

            x = obj.coordinates.x
            y = 600 - obj.coordinates.y

            if obj.name == "background":
                self.manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture("assets/ui/sprites/bagUi.png"),
                        width=w,
                        height=h,
                        x=x,
                        y=y,
                    )
                )
            elif "Arrow" in obj.name:
                self.manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture(
                            f"assets/ui/sprites/{obj.name}.png"
                        ),
                        width=w,
                        height=h,
                        x=x,
                        y=y,
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
                    align="center",
                )
                self.manager.add(self.sectionText)
            elif obj.name == "bag":
                self.bag = arcade.gui.UIImage(
                    texture=arcade.load_texture("assets/ui/sprites/bagItem.png"),
                    width=w,
                    height=h,
                    x=x,
                    y=y,
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
                    multiline=True,
                )
                self.manager.add(self.dialog)

        self.bagItemTexture = arcade.load_texture("assets/ui/sprites/bagItem.png")
        self.bagPokeballTexture = arcade.load_texture(
            "assets/ui/sprites/bagPokeball.png"
        )

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
            font_size=20,
        )

    def setup_invetory(self):
        for item in self.itemLabels:
            self.manager.remove(item)

        self.currentIndex = 0
        self.itemLabels.clear()

        for i in range(MAX_VISIBLE_ITEMS):
            label = arcade.gui.UILabel(
                text="",
                x=self.startX,
                y=self.startY - (i * self.spacing),
                width=250,
                height=self.spacing,
                text_color=arcade.color.BLACK,
                font_name="Pokemon Emerald",
                font_size=30,
            )
            self.itemLabels.append(label)
            self.manager.add(label)

    def change_bag(self, bag: str):
        self.sectionText.text = bag.upper()
        if bag == "items":
            self.bag.texture = self.bagItemTexture
        elif bag == "pokeball":
            self.bag.texture = self.bagPokeballTexture
        elif bag == "berry":
            self.bag.texture = self.bagPokeballTexture

    def set_y_of_cursor(self, index: int):
        self.cursorLabel.y = self.startY - (index * self.spacing) + (self.spacing / 3)

    def set_text(self, text: str):
        self.dialog.text = text

    def draw(self):
        self.manager.draw()
        self.cursorLabel.draw()
