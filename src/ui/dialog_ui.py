import arcade
import arcade.gui
from src.ui.components.typewriter_message_box import TypewriterMessageBox

class DialogUI:
    def __init__(self, after_text_callback):
        self._manager = arcade.gui.UIManager()
        self._message_box = TypewriterMessageBox(None, self._manager)
        self._message_box.set_callback(after_text_callback)
        
    def draw(self):
        self._manager.draw()