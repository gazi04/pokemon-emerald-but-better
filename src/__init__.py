import arcade

# 1. Define Constants for easy adjustments
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "My Simple Arcade App"

class MyGame(arcade.Window):
    def __init__(self):
        super().__init__(800, 600, "TMX Map Renderer")
        self.tile_map = None
        self.scene = None

    def setup(self):
        map_name = "assets/map/littleroot_town.tmx"
    
        tile_scaling = 2
        
        self.tile_map = arcade.tilemap.load_tilemap(map_name, tile_scaling)

        self.scene = arcade.Scene.from_tilemap(self.tile_map)

    def on_draw(self):
        self.clear()
        self.scene.draw()

def main():
    """ Main function """
    window = MyGame()
    window.setup()
    arcade.run()

if __name__ == "__main__":
    main()