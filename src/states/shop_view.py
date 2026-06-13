import arcade
from src.core.data_loader import DataLoader
from src.core.save_manager import SaveManager
from data.config import Config
from src.core.event_bus import global_bus
from src.ui.shop_ui import ShopUI

CONFIG = Config.load()

class ShopView(arcade.View):
    def __init__(self, overworld: arcade.View, previous_view: arcade.View, data_loader: DataLoader, save_manager: SaveManager):
        super().__init__()
        
        self.items = data_loader.items
        
        self.ui = ShopUI(self.items)
        self.overworld = overworld
        
    def on_draw(self):
        self.clear()
        self.overworld.on_draw()
        self.ui.draw()