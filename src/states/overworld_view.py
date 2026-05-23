import arcade
from src.states.battleView import BattleView
from src.states.menuView import MenuView
from data.config import Config
from src.constants import FLICKER_INTERVAL, FONT, CAMERA_LERP_SPEED

# New architectural imports
from src.model.player import PlayerState
from src.controllers.player_input import PlayerInput
from src.systems.movement_system import MovementSystem
from src.systems.encounter_system import EncounterSystem
from src.entities.player_sprite import PlayerSprite

CONFIG = Config.load()


class OverworldView(arcade.View):
    def __init__(self):
        super().__init__()

        arcade.get_window().ctx.default_texture_filter = (
            arcade.gl.NEAREST,
            arcade.gl.NEAREST,
        )

        arcade.load_font(FONT)

        # Initialize modular player architecture
        self.player_state = PlayerState()
        self.player_input = PlayerInput()
        self.movement_system = MovementSystem()
        self.encounter_system = EncounterSystem()
        self.player_sprite = PlayerSprite()

        self.keys = set()
        self.camera = None

        self.transitionActive = False
        self.transitionTimer = 0.0
        self.maxTransitionTime = 0.8
        self.canRenderScene = True
        self.flickerInterval = FLICKER_INTERVAL

        self.setup()

        position = (
            self.tile_map.get_tilemap_layer("position").tiled_objects[0].coordinates
        )

        # Re-implement teleport logic on the data rather than via the old controller
        self.player_state.pixel_x = position.x * 2
        self.player_state.pixel_y = position.y / 2 - 110

    def setup(self, map=None, playerPos=None):
        layer_options = {
            "collision": {"use_spatial_hash": True},
            "bush": {"use_spatial_hash": True},
            "transitions": {"use_spatial_hash": True},
        }
        self.tile_map = arcade.tilemap.load_tilemap(
            map or CONFIG.game.starting_map, scaling=2.0, layer_options=layer_options
        )
        self.scene = arcade.Scene.from_tilemap(self.tile_map)

        if playerPos:
            self.player_state.pixel_x = playerPos[0]
            self.player_state.pixel_y = playerPos[1]

        self.camera = arcade.Camera2D()

    def on_update(self, delta_time):
        if self.transitionActive:
            self.transitionTimer += delta_time

            if int(self.transitionTimer / self.flickerInterval) % 2 == 0:
                self.canRenderScene = True
            else:
                self.canRenderScene = False

            if self.transitionTimer >= self.maxTransitionTime:
                name, level, data = self.pending_battle_data
                self.window.show_view(BattleView(name, data, level, self))
                self.keys.clear()

                self.transitionActive = False
                self.canRenderScene = True
                self.transitionTimer = 0.0
            return

        self.camera.position = arcade.math.lerp_2d(
            self.camera.position,
            (self.player_state.pixel_x, self.player_state.pixel_y),
            CAMERA_LERP_SPEED,
        )

        intent = self.player_input.process_input(
            self.player_state,
            self.keys,
            CONFIG.controls,
            self.scene["collision"],
            self.scene["transitions"],
        )

        if intent and intent["type"] == "transition":
            path = f"assets/map/{intent['map']}.tmx"
            self.player_state.map_name = intent["map"]
            self.setup(path, [intent["x"], intent["y"]])
            intent = None # consume the intent

        events = self.movement_system.update(delta_time, self.player_state, intent)

        self.player_sprite.sync_with_state(self.player_state)

        for event in events:
            if event["type"] == "finished_moving":
                encounter_result = self.encounter_system.check_encounter(
                    self.player_state, self.scene["bush"]
                )
                if encounter_result:
                    self.startBattle(
                        encounter_result["name"],
                        encounter_result["level"],
                        encounter_result["data"],
                    )

    def on_draw(self):
        self.clear()
        self.camera.use()

        if self.scene and self.canRenderScene:
            self.scene.draw(pixelated=True)

        self.player_sprite.draw()

    def on_key_press(self, key, _):
        self.keys.add(key)

        if self.isPressed(CONFIG.controls.bag, key):
            self.keys.clear()
            self.window.show_view(MenuView(self))

    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key

    def on_key_release(self, key, _):
        self.keys.discard(key)

    def startBattle(self, name, level, data):
        self.transitionActive = True
        self.transitionTimer = 0.0
        self.pending_battle_data = (name, level, data)

