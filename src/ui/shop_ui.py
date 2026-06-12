import arcade
import arcade.gui
from src.model.item import Item
from src.constants import SHOP_UI

class ShopUI:
    def __init__(self, item: dict[str, Item]):
        self._manager = arcade.gui.UIManager()
        self._manager._pixelated = True
        
        tilemap = arcade.load_tilemap(SHOP_UI)
        uiLayer = tilemap.get_tilemap_layer("ui")
        
    def draw(self):
        self._manager.draw()