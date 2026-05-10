import arcade
from data.config import Config
from src.states.bagView import BagView
from src.ui.menuUi import MenuUi

CONFIG = Config.load()

class MenuView(arcade.View):
    def __init__(self, overworld:arcade.View):
        super().__init__()
        
        self.overworld = overworld
        self.ui = MenuUi()
        
    def on_draw(self):
        self.clear()
        
        self.overworld.on_draw()
        
        self.ui.draw()
    
    def on_key_press(self, key, modifiers):
        if self.isPressed(CONFIG.controls.cancel, key):
            self.window.show_view(self.overworld)
    
    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key
    