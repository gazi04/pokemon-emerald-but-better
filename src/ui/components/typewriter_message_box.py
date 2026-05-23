import arcade
import arcade.gui
from src.constants import TEXT_DELAY

class TypewriterMessageBox(arcade.gui.UIWidget):
    """
    Dedicated component to animating text on screen. 
    Doesn't know about game rules or UI states.
    """
    def __init__(self, x: float, y: float, width: float, height: float):
        super().__init__(x=x, y=y, width=width, height=height)

        self.background_texture = arcade.load_texture("assets/ui/sprites/dialogbox.png")
        self.background = arcade.gui.UIImage(
            x=x, y=y, width=width, height=height, texture=self.background_texture
        )
        self.add(self.background)

        # y - h equivalent from original code
        self.dialog_text = arcade.gui.UILabel(
            x=x,
            y=y - height, # Using the raw bounds parsed from tiled
            width=width,
            height=height,
            text_color=arcade.color.WHITE,
            font_name="Pokemon Emerald",
            font_size=25,
            align="left",
            multiline=True,
        )
        self.add(self.dialog_text)

        self.target_text = ""
        self.current_text = ""
        self.text_delay_timer = 0.0
        self.is_processing = False

        self.message_queue = []
        self.after_text_callback = None

    def queue_message(self, message: str):
        self.message_queue.append(message)
        if not self.is_processing:
            self._next_message()

    def set_callback(self, callback):
        self.after_text_callback = callback

    def _next_message(self):
        if self.message_queue:
            self.target_text = self.message_queue.pop(0)
            self.current_text = ""
            self.dialog_text.text = ""
            self.is_processing = True
            self.text_delay_timer = 0.0
        else:
            self.is_processing = False
            if self.after_text_callback:
                self.after_text_callback()

    def update(self, delta_time: float):
        if not self.is_processing:
            return

        self.text_delay_timer += delta_time

        if len(self.current_text) < len(self.target_text):
            if self.text_delay_timer > TEXT_DELAY:
                self.current_text += self.target_text[len(self.current_text)]
                self.dialog_text.text = self.current_text
                
                # trigger redraw
                self.dialog_text.trigger_full_render()
                self.background.trigger_full_render()
                
                self.text_delay_timer = 0.0
        else:
            if self.text_delay_timer > 1.5:
                self._next_message()
