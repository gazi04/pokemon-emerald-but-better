import arcade
from src.core.data_loader import DataLoader
from src.core.save_manager import SaveManager
from data.config import Config
from src.core.event_bus import global_bus
from src.core.events import CloseViewEvent, OverlayViewEvent
from src.ui.menu_ui import MenuUi

CONFIG = Config.load()


class MenuView(arcade.View):
    def __init__(
        self, overworld: arcade.View, save_manager: SaveManager, data_loader: DataLoader
    ):
        super().__init__()

        self.overworld = overworld
        self.save_manager = save_manager
        self.data_loader = data_loader
        self.ui = MenuUi()
        self.selectedIndex = 0

    def on_draw(self):
        self.clear()
        # Draw the live Overworld behind the menu — no references to BagView etc.
        self.overworld.on_draw()
        arcade.get_window().default_camera.use()
        self.ui.draw()

    def on_key_press(self, symbol: int, modifiers: int):
        if self.isPressed(CONFIG.controls.interact, symbol):
            self.action()
        elif self.isPressed(CONFIG.controls.up, symbol):
            self.selectedIndex -= 1
            if self.selectedIndex == -1:
                self.selectedIndex = len(self.ui.buttons) - 1
            self.ui.setYOfCursor(self.selectedIndex)
        elif self.isPressed(CONFIG.controls.down, symbol):
            self.selectedIndex += 1
            if self.selectedIndex == len(self.ui.buttons):
                self.selectedIndex = 0
            self.ui.setYOfCursor(self.selectedIndex)
        elif self.isPressed(CONFIG.controls.cancel, symbol):
            global_bus.publish(CloseViewEvent())

    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key

    def action(self):
        if self.selectedIndex == 0:
            global_bus.publish(
                OverlayViewEvent(
                    target="pokedex",
                    payload={
                        "previous_view": self,
                        "save_manager": self.save_manager,
                        "data_loader": self.data_loader,
                    },
                )
            )
        elif self.selectedIndex == 1:
            global_bus.publish(
                OverlayViewEvent(
                    target="pokemon_menu",
                    payload={
                        "previous_view": self,
                        "save_manager": self.save_manager,
                        "data_loader": self.data_loader,
                    },
                )
            )
        elif self.selectedIndex == 2:
            global_bus.publish(
                OverlayViewEvent(
                    target="bag",
                    payload={
                        "previous_view": self,
                        "save_manager": self.save_manager,
                        "data_loader": self.data_loader,
                    },
                )
            )
        elif self.selectedIndex == 3:
            pass  # reserved
