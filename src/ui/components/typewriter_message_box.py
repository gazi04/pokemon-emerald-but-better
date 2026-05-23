import arcade
import arcade.gui
from src.constants import TEXT_DELAY


class TypewriterMessageBox:
    """
    Dedicated component to animating text on screen.
    Manages the dialogbox sprite and dialog text label directly,
    added to an external UIManager by the orchestrator.
    """
    def __init__(self, bounds: dict, manager: arcade.gui.UIManager):
        b = bounds.get("dialogBox", {"x": 0, "y": 0, "w": 800, "h": 200})
        self._manager = manager

        self.background = arcade.gui.UIImage(
            x=b["x"],
            y=b["y"],
            width=b["w"],
            height=b["h"],
            texture=arcade.load_texture("assets/ui/sprites/dialogbox.png"),
        )

        d = bounds.get("dialog", {"x": b["x"], "y": b["y"], "w": b["w"], "h": b["h"]})
        self.dialog_text = arcade.gui.UILabel(
            x=d["x"],
            y=d["y"] - d["h"],
            width=d["w"],
            height=d["h"],
            text_color=arcade.color.WHITE,
            font_name="Pokemon Emerald",
            font_size=25,
            align="left",
            multiline=True,
        )

        self.target_text = ""
        self.current_text = ""
        self.text_delay_timer = 0.0
        self.is_processing = False
        self.message_queue = []
        self.after_text_callback = None

    def show(self):
        self._manager.add(self.background)
        self._manager.add(self.dialog_text)

    def hide(self):
        self._manager.remove(self.background)
        self._manager.remove(self.dialog_text)

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
            self.dialog_text.trigger_full_render()
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
                self.dialog_text.trigger_full_render()
                self.background.trigger_full_render()
                self.text_delay_timer = 0.0
        else:
            if self.text_delay_timer > 1.5:
                self._next_message()
