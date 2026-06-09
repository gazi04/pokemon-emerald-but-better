import arcade
from typing import Optional
from src.core.data_loader import DataLoader
from src.core.save_manager import SaveManager
from data.config import Config
from src.ui.pokedex_ui import PodedexUi

CONFIG = Config.load()

class PokedexView(arcade.View):
    def __init__(self,     
            previousView: arcade.View,
            save_manager: SaveManager,
            data_loader: DataLoader,
        ):
        super().__init__()
        
        self.ui = PodedexUi()
        
    def on_draw(self):
        self.clear()
        self.ui.draw()
        