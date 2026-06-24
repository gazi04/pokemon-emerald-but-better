import arcade
from src.ui.dialog_ui import DialogUI
from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from src.core.message_service import MessageService
from src.states.base_view import GameView
from data.config import Config

CONFIG = Config.load()


class DialogView(GameView):
    def __init__(
        self,
        overworld: arcade.View,
        data_loader: DataLoader,
        player_manager: PlayerManager,
        message_service: MessageService,
        after_text_callback,
        npc_id: str,
        state: str = "default",
    ):
        super().__init__()

        self.overworld = overworld
        self.player_manager = player_manager
        self.message_service = message_service
        self.ui = DialogUI()

        self.npc = data_loader.npc_dialog[npc_id]
        self.npc_id = npc_id
        # The caller may override what happens after the dialog (e.g. a beaten
        # trainer should just close instead of fighting again).
        self.action = self.npc.action_after_dialog
        self.dialog_index = 0
        self.dialog = self.npc.get_dialog(state)

        self.ui.queue_messages(self.dialog[self.dialog_index])

    def on_show_view(self):
        self.message_service.set_box(self.ui.message_box)

    def on_key_press(self, key: int, modifiers: int):
        if self.is_pressed(CONFIG.controls.cancel, key) and self.ui.is_text_finished():
            if self.dialog_index < len(self.dialog) - 1:
                self.dialog_index += 1
                self.ui.queue_messages(self.dialog[self.dialog_index])
            else:
                self._end_of_dialog()

    def _end_of_dialog(self):
        if self.action == "shop":
            self.overlay("shop")
        elif self.action == "fight":
            self.swap(
                "battle_trainer",
                trainer_data=self.npc.team,
                npc_id=self.npc_id,
            )
        elif self.action == "heal":
            self.player_manager.heal_team()
            self.close()
        else:
            self.close()

    def on_draw(self):
        self.clear()

        self.overworld.on_draw()
        arcade.get_window().default_camera.use()
        self.ui.draw()
