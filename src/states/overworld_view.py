import arcade
from data.config import Config
from src.constants import FLICKER_INTERVAL, FONT, CAMERA_LERP_SPEED, TILE_SIZE

from src.core.save_manager import SaveManager
from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from src.model.motion.player_motion import PlayerMotion
from src.controllers.player_input import PlayerInput
from src.systems.movement_system import MovementSystem
from src.systems.encounter_system import EncounterSystem
from src.systems.npc_controller import NpcController
from src.systems.npc_behaviors import make_behavior
from src.entities.player_sprite import PlayerSprite
from src.entities.npc import Npc
from src.core.event_bus import global_bus
from src.core.events import (
    BattleEncounterTriggeredEvent,
    NpcInteractEvent,
    SwapViewEvent,
    OverlayViewEvent,
)

CONFIG = Config.load()

# Where the player respawns after whiting out. Matches the Poké Center door
# entrance (see the "door_pokecenter" transition in littleroot_town.tmx).
POKECENTER_MAP = "oldale_town/pokemon_center"
POKECENTER_SPAWN = (496, 210)


class OverworldView(arcade.View):
    def __init__(self, player_manager: PlayerManager, data_loader: DataLoader):
        super().__init__()

        self.player_manager = player_manager
        self.save_manager = player_manager.save_manager
        self.data_loader = data_loader

        arcade.get_window().ctx.default_texture_filter = (
            arcade.gl.NEAREST,
            arcade.gl.NEAREST,
        )
        arcade.load_font(FONT)

        self.player_state = PlayerMotion()
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

        saved = self.save_manager.saved_position
        if saved:
            self.player_state.map_name = saved.get(
                "map_name", self.player_state.map_name
            )
            self.player_state.direction = saved.get(
                "direction", self.player_state.direction
            )
            map_path = f"assets/map/{self.player_state.map_name}.tmx"
            self.setup(map_path)
            self.player_state.pixel_x = saved["pixel_x"]
            self.player_state.pixel_y = saved["pixel_y"]
        else:
            self.setup()
            position = (
                self.tile_map.get_tilemap_layer("position").tiled_objects[0].coordinates
            )
            self.player_state.pixel_x = position.x * 2
            self.player_state.pixel_y = position.y / 2 - 110

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def _subscribe(self):
        global_bus.subscribe(BattleEncounterTriggeredEvent, self._on_battle_triggered)
        global_bus.subscribe(NpcInteractEvent, self._on_npc_interaction)

    def _unsubscribe(self):
        global_bus.unsubscribe(BattleEncounterTriggeredEvent, self._on_battle_triggered)
        global_bus.unsubscribe(NpcInteractEvent, self._on_npc_interaction)
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

        self.npcs = arcade.SpriteList(use_spatial_hash=False)
        npc_layer = self.tile_map.get_tilemap_layer("npc")
        if npc_layer:
            self.scene.remove_sprite_list_by_name("npc")
            for obj in npc_layer.tiled_objects:
                props = obj.properties or {}
                npc = Npc(
                    x=obj.coordinates.x * 2 + obj.size.width,
                    y=(
                        self.tile_map.height * self.tile_map.tile_height
                        - obj.coordinates.y
                    )
                    * 2
                    + obj.size.height / 2,
                    npc_id=props.get("npc_id", ""),
                    behavior=make_behavior(props),
                    facing=props.get("facing", "down"),
                )
                self.npcs.append(npc)

        self._setup_npc_controller()

        if playerPos:
            self.player_state.pixel_x = playerPos[0]
            self.player_state.pixel_y = playerPos[1]

        self.camera = arcade.Camera2D()

        if self.encounter_system:
            self.encounter_system.cleanup()

        bush_tiles = self._extract_bush_tiles()

        self.encounter_system = EncounterSystem(
            bush_tiles=bush_tiles,
            player_state=self.player_state,
            data_loader=self.data_loader,
        )

    def _setup_npc_controller(self) -> None:
        """Build the NPC controller for the freshly loaded map."""
        try:
            collision_tiles = self.scene["collision"]
        except KeyError:
            collision_tiles = arcade.SpriteList()

        map_width = self.tile_map.width * self.tile_map.tile_width * 2
        map_height = self.tile_map.height * self.tile_map.tile_height * 2

        self.npc_controller = NpcController(
            npcs=self.npcs,
            movement_system=self.movement_system,
            collision_tiles=collision_tiles,
            player_state=self.player_state,
            map_width=map_width,
            map_height=map_height,
        )

    def _extract_bush_tiles(self) -> set[tuple[int, int]]:
        """
        Build a set of integer (grid_x, grid_y) tuples from the bush
        SpriteList. Done once at map load — O(1) lookup at runtime.
        The bush layer sprites are scaled 2x, but their center_x/center_y
        are in pixel space. Dividing by TILE_SIZE gives grid coords that
        match MovementSystem's grid_x = round(pixel_x / TILE_SIZE).
        """
        try:
            tiles: set[tuple[int, int]] = set()
            bush_layer = self.scene["bush"]
            for sprite in bush_layer:
                gx = round(sprite.center_x / TILE_SIZE)
                gy = round(sprite.center_y / TILE_SIZE)
                tiles.add((gx, gy))
            return tiles
        except Exception:
            return set()

    def respawn_at_pokecenter(self) -> None:
        """Relocate the player to the Poké Center entrance (used after whiting out)."""
        self.player_state.map_name = POKECENTER_MAP
        self.player_state.direction = "up"
        self.setup(
            f"assets/map/{POKECENTER_MAP}.tmx",
            [POKECENTER_SPAWN[0], POKECENTER_SPAWN[1]],
        )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_battle_triggered(self, event: BattleEncounterTriggeredEvent):
        self._start_battle_transition(
            event.pokemon_name, event.pokemon_level, event.pokemon_data
        )

    def _on_npc_interaction(self, event: NpcInteractEvent):
        npc_id = event.npc_id

        if npc_id == "poke-mart-npc":
            global_bus.publish(
                OverlayViewEvent(
                    target="shop",
                    payload={
                        "previous_view": self,
                        "save_manager": self.save_manager,
                        "data_loader": self.data_loader,
                    },
                )
            )
            return

        npc = self.data_loader.npc_dialog.get(npc_id)
        if npc is None:
            return

        state, action = self._resolve_dialog(npc_id, npc)
        self.player_manager.npc_manager.mark_talked(npc_id)

        global_bus.publish(
            OverlayViewEvent(
                target="dialog",
                payload={"npc_id": npc_id, "state": state, "action": action},
            )
        )

    def _resolve_dialog(self, npc_id: str, npc) -> tuple[str, str]:
        """
        Pick which dialog state to show and what happens after it,
        based on the NPC's battle progress.
        Returns (state, action_after_dialog).
        """
        is_battle_npc = npc.action_after_dialog == "fight"
        already_beaten = not self.player_manager.npc_manager.can_fight(npc_id)

        if is_battle_npc and not already_beaten:
            return "first_encounter", "fight"
        if is_battle_npc and already_beaten:
            return "after_victory", "end"
        return "default", npc.action_after_dialog

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
            self.npcs,
        )

        if intent and intent["type"] == "transition":
            path = f"assets/map/{intent['map']}.tmx"
            self.player_state.map_name = intent["map"]
            self.setup(path, [intent["x"], intent["y"]])
            intent = None

        self.movement_system.update(delta_time, self.player_state, intent)
        self.player_sprite.sync_with_state(self.player_state)

        # NPCs only think while the overworld is the active view, so they
        # naturally freeze during dialog, battle and menus.
        self.npc_controller.update(delta_time)

    def on_draw(self):
        self.clear()
        self.camera.use()
        if self.scene and self.canRenderScene:
            self.scene.draw(pixelated=True)
        self.npcs.draw(pixelated=True)
        self.player_sprite.draw()

    def on_key_press(self, key, _):
        self.keys.add(key)
        if self.is_pressed(CONFIG.controls.bag, key):
            self.keys.clear()
            global_bus.publish(
                OverlayViewEvent(
                    target="menu",
                    payload={
                        "save_manager": self.save_manager,
                        "data_loader": self.data_loader,
                    },
                )
            )

    def is_pressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key

    def on_key_release(self, key, _):
        self.keys.discard(key)

    def _start_battle_transition(self, name, level, data):
        self.transitionActive = True
        self.transitionTimer = 0.0
        self.pending_battle_data = (name, level, data)
