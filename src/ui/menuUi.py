import arcade
import arcade.gui


class MenuUi:
    def __init__(self):
        self._manager = arcade.gui.UIManager()
        self._manager._pixelated = True

        tilemap = arcade.load_tilemap("assets/ui/menuUiDesign.tmx")
        uiLayout = tilemap.get_tilemap_layer("ui")

        self.buttons: list[arcade.gui.UILabel] = []

        for obj in uiLayout.tiled_objects:
            w = obj.size.width
            h = obj.size.height

            x = obj.coordinates.x
            y = 600 - obj.coordinates.y

            if obj.name == "background":
                self._manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture("assets/ui/sprites/box2.png"),
                        width=w,
                        height=h,
                        x=x,
                        y=y,
                    )
                )
            else:
                button = arcade.gui.UILabel(
                    obj.name.capitalize(),
                    text_color=arcade.color.BLACK,
                    font_name="Pokemon Emerald",
                    font_size=35,
                    x=x,
                    y=y - h,
                    width=w,
                    height=h,
                )

                self.buttons.append(button)
                self._manager.add(button)

        self._cursorLabel = arcade.Text(
            text="▶",
            x=0,
            y=0,
            align="center",
            color=arcade.color.BLACK,
            font_name="Pokemon Emerald",
            font_size=35,
        )
        self.setYOfCursor(0)

    def draw(self):
        self._manager.draw()

        self._cursorLabel.draw()

    def setYOfCursor(self, index: int):
        self._cursorLabel.x = self.buttons[index].rect.left - 30
        self._cursorLabel.y = self.buttons[index].rect.center_y - 13
