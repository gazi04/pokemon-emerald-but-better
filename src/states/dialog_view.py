import arcade
from src.ui.dialog_ui import DialogUI

class DialogView(arcade.View):
    def __init__(self, overworld: arcade.View, after_text_callback):
        super().__init__()
        
        self.overworld = overworld
        self.ui = DialogUI(after_text_callback)
        
    def on_update(self, delta_time):
        self.ui.update(delta_time)

    def on_draw(self):
        self.clear()

        self.overworld.on_draw()
        arcade.get_window().default_camera.use()
        self.ui.draw()