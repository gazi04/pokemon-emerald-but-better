import arcade
from data.config import Config
from src.core.event_bus import global_bus
from src.core.events import (
    CloseViewEvent,
    OverlayViewEvent,
    SaveGameRequestEvent,
    SaveCompletedEvent,
)
from src.ui.menu_ui import MenuUi
from src.constants import FONT

CONFIG = Config.load()


class MenuView(arcade.View):
    def __init__(self, overworld: arcade.View):
        super().__init__()

        self.overworld = overworld
        self.ui = MenuUi()
        self.selectedIndex = 0

        self._save_feedback: str = ""
        self._save_feedback_timer: float = 0.0

        global_bus.subscribe(SaveCompletedEvent, self._on_save_completed)

    def on_show_view(self):
        global_bus.subscribe(SaveCompletedEvent, self._on_save_completed)

    def on_hide_view(self):
        global_bus.unsubscribe(SaveCompletedEvent, self._on_save_completed)

    def _on_save_completed(self, event: SaveCompletedEvent):
        self._save_feedback = "Game saved!" if event.success else "Save failed!"
        self._save_feedback_timer = 2.0

    def on_update(self, delta_time: float):
        if self._save_feedback_timer > 0:
            self._save_feedback_timer -= delta_time
            if self._save_feedback_timer <= 0:
                self._save_feedback = ""

    def on_draw(self):
        self.clear()
        # Draw the live Overworld behind the menu — no references to BagView etc.
        self.overworld.on_draw()
        arcade.get_window().default_camera.use()
        self.ui.draw()
        if self._save_feedback:
            arcade.draw_text(
                self._save_feedback,
                x=400,
                y=20,
                color=arcade.color.WHITE,
                font_size=20,
                font_name=FONT,
                anchor_x="center",
            )

    def on_key_press(self, symbol: int, modifiers: int):
        if self.is_pressed(CONFIG.controls.interact, symbol):
            self.action()
        elif self.is_pressed(CONFIG.controls.up, symbol):
            self.selectedIndex -= 1
            if self.selectedIndex == -1:
                self.selectedIndex = len(self.ui.buttons) - 1
            self.ui.set_y_of_cursor(self.selectedIndex)
        elif self.is_pressed(CONFIG.controls.down, symbol):
            self.selectedIndex += 1
            if self.selectedIndex == len(self.ui.buttons):
                self.selectedIndex = 0
            self.ui.set_y_of_cursor(self.selectedIndex)
        elif self.is_pressed(CONFIG.controls.cancel, symbol):
            global_bus.publish(CloseViewEvent())

    def is_pressed(self, config_key, key) -> bool:
        return getattr(arcade.key, config_key, None) == key

    def action(self):
        if self.selectedIndex == 0:
            global_bus.publish(
                OverlayViewEvent(
                    target="pokedex",
                    payload={
                        "previous_view": self,
                    },
                )
            )
        elif self.selectedIndex == 1:
            global_bus.publish(
                OverlayViewEvent(
                    target="pokemon_menu",
                    payload={
                        "previous_view": self,
                    },
                )
            )
        elif self.selectedIndex == 2:
            global_bus.publish(
                OverlayViewEvent(
                    target="bag",
                    payload={
                        "previous_view": self,
                    },
                )
            )
        elif self.selectedIndex == 3:
            global_bus.publish(SaveGameRequestEvent())
