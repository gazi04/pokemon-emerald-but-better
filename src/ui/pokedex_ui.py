import arcade
import arcade.gui

class PodedexUi:
    def __init__(self):
        self._manager = arcade.gui.UIManager()
        self._manager._pixelated = True
        
    def draw(self):
        self._manager.draw()