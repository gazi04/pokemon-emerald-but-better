import arcade
from src.entities.playerController import Player
from src.states.battleView import BattleView
from src.states.bagView import BagView
from data.config import Config
from src.constants import FLICKER_INTERVAL, FONT, CAMERA_LERP_SPEED

CONFIG = Config.load()


class OverworldView(arcade.View):
    def __init__(self):
        super().__init__()

        arcade.get_window().ctx.default_texture_filter = (
            arcade.gl.NEAREST,
            arcade.gl.NEAREST,
        )

        arcade.load_font(FONT)

        self.player = Player()

        self.keys = set()
        self.camera = None

        self.transition_active = False
        self.transition_timer = 0.0
        self.max_transition_time = 0.8
        self.canRenderScene = True
        self.flickerInterval = FLICKER_INTERVAL
        
        self.setup()
        
        position = self.tile_map.get_tilemap_layer("position").tiled_objects[0].coordinates
        
        self.player.teleportPlayer(position.x, position.y)
        
        
    def setup(self, map=None, playerPos=None):
        layer_options = {
            "collision": {"use_spatial_hash": True},
            "bush": {"use_spatial_hash": True},
            "transitions": {"use_spatial_hash": True},
        }
        self.tile_map = arcade.tilemap.load_tilemap(
            map or CONFIG.game.starting_map, 
            scaling=2.0,
            layer_options=layer_options
        )
        self.scene = arcade.Scene.from_tilemap(self.tile_map)

        if playerPos:
            self.player.center_x = playerPos[0]
            self.player.center_y = playerPos[1]

        self.camera = arcade.Camera2D()

    def on_update(self, delta_time):
        if self.transition_active:
            self.transition_timer += delta_time

            if int(self.transition_timer / self.flickerInterval) % 2 == 0:
                self.canRenderScene = True
            else:
                self.canRenderScene = False

            if self.transition_timer >= self.max_transition_time:
                name, level, data = self.pending_battle_data
                self.window.show_view(BattleView(name, data, level, self))
                self.keys.clear()

                self.transition_active = False
                self.canRenderScene = True
                self.transition_timer = 0.0
            return

        self.camera.position = arcade.math.lerp_2d(
            self.camera.position, self.player.getPosition(), CAMERA_LERP_SPEED
        )

        result = self.player.update(
            delta_time,
            self.keys,
            self.scene["collision"],
            self.scene["bush"],
            self.scene["transitions"],
            CONFIG.controls,
        )

        if result:
            type = result["type"]

            if type == "encounter":
                name, data, level = result["name"], result["data"], result["level"]
                self.startBattle(name, level, data)
            elif type == "transition":
                path = f"assets/map/{result['map']}.tmx"
                self.player.map = result["map"]
                self.setup(path, [result["x"], result["y"]])

    def on_draw(self):
        self.clear()
        self.camera.use()

        if self.scene and self.canRenderScene:
            self.scene.draw(pixelated=True)

        self.player.draw()

    def on_key_press(self, key, _):
        self.keys.add(key)
        
        if self.isPressed(CONFIG.controls.bag, key):
            self.window.show_view(BagView(self))

    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key

    def on_key_release(self, key, _):
        self.keys.discard(key)

    def startBattle(self, name, level, data):
        self.transition_active = True
        self.transition_timer = 0.0
        self.pending_battle_data = (name, level, data)
