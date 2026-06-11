import arcade
from src.ui.dialog_ui import DialogUI
from src.core.data_loader import DataLoader
from data.config import Config
from src.core.event_bus import global_bus
from src.core.events import CloseViewEvent

CONFIG = Config.load()

class DialogView(arcade.View):
    def __init__(self, overworld: arcade.View, data_loader: DataLoader, after_text_callback, npc_id: str):
        super().__init__()
        
        self.overworld = overworld
        self.ui = DialogUI()
        
        self.dialog_index = 0
        self.dialog = data_loader.npc_dialog[npc_id].dialog
        
        self.ui.queue_messages(self.dialog[self.dialog_index])
        
    def on_update(self, delta_time):
        self.ui.update(delta_time)
        
    def on_key_press(self, key: int, modifiers: int):
        if self._is_pressed(CONFIG.controls.cancel, key) and self.ui.is_text_finished():
            if self.dialog_index < len(self.dialog) - 1:
                self.dialog_index += 1
                self.ui.queue_messages(self.dialog[self.dialog_index])
            else:
                global_bus.publish(CloseViewEvent())

    def _is_pressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key

    def on_draw(self):
        self.clear()

        self.overworld.on_draw()
        arcade.get_window().default_camera.use()
        self.ui.draw()