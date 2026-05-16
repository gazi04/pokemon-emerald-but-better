import arcade
from data.config import Config
from src.states.bagView import BagView
from src.states.pokemonMenuView import PokemonMenuView
from src.ui.menuUi import MenuUi

CONFIG = Config.load()

class MenuView(arcade.View):
    def __init__(self, overworld:arcade.View):
        super().__init__()
        
        self.overworld = overworld
        self.ui = MenuUi()
        self.selectedIndex = 0
        
    def on_draw(self):
        self.clear()
        
        self.overworld.on_draw()
        
        arcade.get_window().default_camera.use()
        self.ui.draw()
    
    def on_key_press(self, key, modifiers):
        if self.isPressed(CONFIG.controls.interact, key):
            self.action()
        elif self.isPressed(CONFIG.controls.up, key):
            self.selectedIndex -= 1
            if self.selectedIndex == -1:
                self.selectedIndex = len(self.ui.buttons) - 1
                
            self.ui.setYOfCursor(self.selectedIndex)
        elif self.isPressed(CONFIG.controls.down, key):
            self.selectedIndex += 1
            if self.selectedIndex == len(self.ui.buttons):
                self.selectedIndex = 0
                
            self.ui.setYOfCursor(self.selectedIndex)
        elif self.isPressed(CONFIG.controls.cancel, key):
            self.window.show_view(self.overworld)
    
    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key
    
    def action(self):
        if self.selectedIndex == 0:
            self.window.show_view(PokemonMenuView(self))
        elif self.selectedIndex == 1:
            self.window.show_view(BagView(self))
        elif self.selectedIndex == 2:
            pass
    