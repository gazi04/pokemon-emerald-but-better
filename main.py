import arcade
from src.entities.player import Player

class MyGame(arcade.Window):
    def __init__(self):
        super().__init__(800, 600, "Pokemon Emerald Clone")
        self.scene = None
        self.player = Player(x=11, y=12)
        self.keys = set()
        self.setup()

    def setup(self):
        # Load your town map
        map_name = "assets/map/littleroot_town.tmx"
        self.tile_map = arcade.tilemap.load_tilemap(map_name, scaling=2.0)
        self.scene = arcade.Scene.from_tilemap(self.tile_map)

    def on_key_press(self, key, modifiers):
        self.keys.add(key)

    def on_key_release(self, key, modifiers):
        self.keys.discard(key)

    def on_update(self, delta_time):
        self.player.update(delta_time, self.keys, self.scene["collision"])

    def on_draw(self):
        self.clear()
        
        # pixelated=True is CRITICAL for Arcade 3.0 pixel art
        if self.scene:
            self.scene.draw(pixelated=True)
            
        self.player.draw()

def main():
    MyGame()
    arcade.run()

if __name__ == "__main__":
    main()
    