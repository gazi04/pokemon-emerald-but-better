import arcade
from src.entities.player import Player
from src.states.battleView import BattleView
from data.config import Config  

CONFIG = Config.load()

class OverworldView(arcade.View):
    def __init__(self):
        super().__init__()

        arcade.get_window().ctx.default_texture_filter = (
            arcade.gl.NEAREST,
            arcade.gl.NEAREST,
        )

        arcade.load_font("assets/fonts/pokemon-emerald.otf")

        self.player = Player(
            x=CONFIG.game.starting_tile_x,
            y=CONFIG.game.starting_tile_y
        )

        self.keys = set()
        self.camera = None

        self.setup()

    def setup(self):
        """Load the map from config"""
        self.tile_map = arcade.tilemap.load_tilemap(
            CONFIG.game.starting_map,
            scaling=2.0
        )
        self.scene = arcade.Scene.from_tilemap(self.tile_map)
        self.camera = arcade.Camera2D()

    def on_update(self, delta_time):
        self.camera.position = arcade.math.lerp_2d(
            self.camera.position, self.player.getPosition(), 0.5
        )

        encounter = self.player.update(
            delta_time,
            self.keys,
            self.scene["collision"],
            self.scene["bush"],
            CONFIG.controls
        )

        if encounter:
            name, data, level = encounter
            self.keys.clear()
            self.window.show_view(BattleView(name, data, level, self))

    def on_draw(self):
        self.clear()
        self.camera.use()

        if self.scene:
            self.scene.draw(pixelated=True)

        self.player.draw()

    def on_key_press(self, key, _):
        self.keys.add(key)

    def on_key_release(self, key, _):
        self.keys.discard(key)
        
        

def main():
    """Start the game"""
    window = arcade.Window(
        width=CONFIG.window.width,
        height=CONFIG.window.height,
        title=CONFIG.window.title,
        fullscreen=CONFIG.window.fullscreen,
        resizable=CONFIG.window.resizable
    )

    start_view = OverworldView()
    window.show_view(start_view)
    arcade.run()


if __name__ == "__main__":
    main()
    