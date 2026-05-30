import arcade
from src.core.dataLoader import DataLoader
from src.core.saveManager import SaveManager
from data.config import Config
from src.constants import FLICKER_INTERVAL, FONT, CAMERA_LERP_SPEED

from src.model.player import PlayerState
from src.controllers.player_input import PlayerInput
from src.systems.movement_system import MovementSystem
from src.systems.encounter_system import EncounterSystem
from src.entities.player_sprite import PlayerSprite
from src.core.event_bus import global_bus
from src.core.events import (
    BattleEncounterTriggeredEvent,
    SwapViewEvent,
    OverlayViewEvent,
)

CONFIG = Config.load()


class OverworldView(arcade.View):
    def __init__(self, save_manager: SaveManager, data_loader: DataLoader):
        super().__init__()

        arcade.get_window().ctx.default_texture_filter = (
            arcade.gl.NEAREST,
            arcade.gl.NEAREST,
        )

        arcade.load_font(FONT)

        self.save_manager = save_manager
        self.data_loader = data_loader

        self.player_state = PlayerState()
        self.player_input = PlayerInput()
        self.movement_system = MovementSystem()
        self.player_sprite = PlayerSprite()
        self.encounter_system = None

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
        self.player_state.pixel_x = position.x * 2
        self.player_state.pixel_y = position.y / 2 - 110

        self._subscribe()

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def _subscribe(self):
        global_bus.subscribe(BattleEncounterTriggeredEvent, self._on_battle_triggered)

    def _unsubscribe(self):
        global_bus.unsubscribe(BattleEncounterTriggeredEvent, self._on_battle_triggered)
        if self.encounter_system:
            self.encounter_system.cleanup()

    def on_show_view(self):
        self._subscribe()
        if self.encounter_system:
            self.encounter_system.resubscribe()

    def on_hide_view(self):
        self._unsubscribe()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

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

        if self.encounter_system:
            self.encounter_system.cleanup()

        self.encounter_system = EncounterSystem(
            bush_layer=self.scene["bush"],
            player_state=self.player_state,
            data_loader=self.data_loader,
        )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_battle_triggered(self, event: BattleEncounterTriggeredEvent):
        """Received from EncounterSystem — start the flicker then hand off."""
        self._start_battle_transition(
            event.pokemon_name, event.pokemon_level, event.pokemon_data
        )

    # ------------------------------------------------------------------
    # Game loop
    # ------------------------------------------------------------------

    def on_update(self, delta_time):
        if self.transitionActive:
            self.transitionTimer += delta_time

            self.canRenderScene = (
                int(self.transitionTimer / self.flickerInterval) % 2 == 0
            )

            if self.transitionTimer >= self.maxTransitionTime:
                name, level, data = self.pending_battle_data
                # Tell the Director to swap to the Battle view
                global_bus.publish(
                    SwapViewEvent(
                        target="battle",
                        payload={
                            "pokemon_name": name,
                            "pokemon_data": data,
                            "pokemon_level": level,
                        },
                    )
                )
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
            intent = None

        self.movement_system.update(delta_time, self.player_state, intent)
        self.player_sprite.sync_with_state(self.player_state)

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
            # Ask the Director to stack the Menu as an overlay
            global_bus.publish(
                OverlayViewEvent(
                    target="menu",
                    payload={
                        "save_manager": self.save_manager,
                        "data_loader": self.data_loader,
                    },
                )
            )

    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key

    def on_key_release(self, key, _):
        self.keys.discard(key)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _start_battle_transition(self, name, level, data):
        self.transitionActive = True
        self.transitionTimer = 0.0
        self.pending_battle_data = (name, level, data)
