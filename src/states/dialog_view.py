import arcade
from src.ui.dialog_ui import DialogUI
from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from src.core.message_service import MessageService
from src.states.base_view import GameView
from data.config import CONFIG


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
        lines: list[str] | None = None,
    ):
        super().__init__()

        self.overworld = overworld
        self.player_manager = player_manager
        self.message_service = message_service
        self.ui = DialogUI()

        self.npc_id = npc_id
        self.dialog_index = 0

        if lines is not None:
            # Speaker-less text (an item pickup, a sign) — no NPC to look up,
            # and nothing to do afterwards but close.
            self.npc = None
            self.action = "end"
            self.dialog = list(lines)
        else:
            self.npc = data_loader.npc_dialog[npc_id]
            # The caller may override what happens after the dialog (e.g. a
            # beaten trainer should just close instead of fighting again).
            self.action = self.npc.action_after_dialog
            self.dialog = self.npc.get_dialog(state)

        self._action_handlers = {
            "shop": self._action_shop,
            "fight": self._action_fight,
            "heal": self._action_heal,
        }

        self.ui.queue_messages(self.dialog[self.dialog_index])

    def on_show_view(self):
        self.message_service.set_box(self.ui.message_box)

    def on_key_press(self, symbol: int, modifiers: int):
        if (
            self.is_pressed(CONFIG.controls.cancel, symbol)
            and self.ui.is_text_finished()
        ):
            if self.dialog_index < len(self.dialog) - 1:
                self.dialog_index += 1
                self.ui.queue_messages(self.dialog[self.dialog_index])
            else:
                self._end_of_dialog()

    def _end_of_dialog(self):
        handler = self._action_handlers.get(self.action, self.close)
        handler()

    def _action_shop(self):
        self.overlay("shop")

    def _action_fight(self):
        # Spend the encounter up front, not on victory — an NPC is fought once
        # whatever the outcome, so whiting out doesn't hand back a rematch.
        self.player_manager.npc_manager.mark_fought(self.npc_id)

        # Hand the battle a copy — it drains the party, and the NpcSpecies team
        # is a shared cached template that must survive for future encounters.
        if self.npc is None or self.npc.team is None:
            return

        self.swap(
            "battle_trainer",
            trainer_data=self.npc.team.clone(),
            npc_id=self.npc_id,
        )

    def _action_heal(self):
        self.player_manager.heal_team()
        self.close()

    def on_draw(self):
        self.clear()

        self.overworld.on_draw()
        arcade.get_window().default_camera.use()
        self.ui.draw()
