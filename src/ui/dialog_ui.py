import arcade
import arcade.gui
from src.ui.components.typewriter_message_box import TypewriterMessageBox
from src.constants import DIALOG_UI
from src.tiled import object_layer


class DialogUI:
    def __init__(self):
        self._manager = arcade.gui.UIManager()

        tilemap = arcade.load_tilemap(DIALOG_UI)
        ui_layer = object_layer(tilemap, "ui")

        self._textbound = {}

        for obj in ui_layer.tiled_objects:
            w = obj.size.width
            h = obj.size.height

            x = obj.coordinates.x
            y = 600 - obj.coordinates.y

            if obj.name == "box":
                self._manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture("assets/ui/sprites/box.png"),
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                    )
                )
            else:
                self._textbound["dialog"] = {"x": x, "y": y, "w": w, "h": h}

        self.message_box = TypewriterMessageBox(self._textbound, self._manager)
        self.message_box.set_font_style(font_color=arcade.color.BLACK)
        self.message_box.show()

    def queue_messages(self, message: str):
        self.message_box.queue_message(message)

    def is_text_finished(self) -> bool:
        return not self.message_box.is_processing

    def update(self, delta_time: float):
        self.message_box.update(delta_time)

    def draw(self):
        self._manager.draw()
