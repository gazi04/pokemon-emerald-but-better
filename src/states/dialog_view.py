import arcade
from src.ui.dialog_ui import DialogUI
from src.core.data_loader import DataLoader
from data.config import Config
from src.core.event_bus import global_bus
from src.core.events import CloseViewEvent, OverlayViewEvent, SwapViewEvent

CONFIG = Config.load()

class DialogView(arcade.View):
    def __init__(self, overworld: arcade.View, data_loader: DataLoader, after_text_callback, npc_id: str, state: str = "default", action: str = None):
        super().__init__()

        self.overworld = overworld
        self.ui = DialogUI()

        self.npc = data_loader.npc_dialog[npc_id]
        self.npc_id = npc_id
        # The caller may override what happens after the dialog (e.g. a beaten
        # trainer should just close instead of fighting again).
        self.action = action if action is not None else self.npc.action_after_dialog
        self.dialog_index = 0
        self.dialog = self.npc.get_dialog(state)

        self.ui.queue_messages(self.dialog[self.dialog_index])
        
    def on_update(self, delta_time):
        self.ui.update(delta_time)
        
    def on_key_press(self, key: int, modifiers: int):
        if self._is_pressed(CONFIG.controls.cancel, key) and self.ui.is_text_finished():
            if self.dialog_index < len(self.dialog) - 1:
                self.dialog_index += 1
                self.ui.queue_messages(self.dialog[self.dialog_index])
            else:
                self._end_of_dialog()
                
    def _end_of_dialog(self):
        if self.action == "shop":
            global_bus.publish(OverlayViewEvent(target="shop"))
        elif self.action == "fight":
            global_bus.publish(SwapViewEvent(
                "battle_trainer",
                {"trainer_data": self.npc.team, "npc_id": self.npc_id},
            ))
        else:
            global_bus.publish(CloseViewEvent())

    def _is_pressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key

    def on_draw(self):
        self.clear()

        self.overworld.on_draw()
        arcade.get_window().default_camera.use()
        self.ui.draw()