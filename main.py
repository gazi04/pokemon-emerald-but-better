import arcade
from src.entities.player import Player
from src.states.battleView import BattleView

class OverworldView(arcade.View):
    def __init__(self):
        super().__init__()
        arcade.get_window().ctx.default_texture_filter = (arcade.gl.NEAREST, arcade.gl.NEAREST)
        
        arcade.load_font("assets/fonts/pokemon-emerald.otf")
        
        self.player = Player(x=11, y=12)
        self.keys = set()
        self.camera = None
        self.setup()

    def setup(self):
        map_name = "assets/map/littleroot_town.tmx"
        self.tile_map = arcade.tilemap.load_tilemap(map_name, scaling=2.0)
        self.scene = arcade.Scene.from_tilemap(self.tile_map)
        self.camera = arcade.Camera2D()

    def on_update(self, delta_time):
        self.camera.position = arcade.math.lerp_2d(
            self.camera.position, self.player.getPosition(), 0.5
        )
        
        encounter = self.player.update(
            delta_time, self.keys, self.scene["collision"], self.scene["bush"]
        )

        if encounter:
            name, data = encounter
            self.keys.clear()
            self.window.show_view(BattleView(name, data, self))

    def on_draw(self):
        self.clear()
        self.camera.use()
        if self.scene:
            self.scene.draw(pixelated=True)
        self.player.draw()

    def on_key_press(self, key, _): self.keys.add(key)
    def on_key_release(self, key, _): self.keys.discard(key)


# --- 2. THE STARTING LINE (Functions) ---

def main():
    window = arcade.Window(800, 600, "Pokemon Emerald Clone", antialiasing=False)
    start_view = OverworldView()
    window.show_view(start_view)
    arcade.run()


if __name__ == "__main__":
    main()
    