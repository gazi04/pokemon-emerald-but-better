import arcade
from data.config import Config
from src.constants import FONT, CAMERA_LERP_SPEED

from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from src.core.message_service import MessageService
from src.model.motion.player_motion import PlayerMotion
from src.controllers.player_input import PlayerInput
from src.systems.movement_system import MovementSystem
from src.systems.encounter_system import EncounterSystem
from src.entities.player_sprite import PlayerSprite
from src.core.event_bus import global_bus
from src.core.events import (
    BattleEncounterTriggeredEvent,
    NpcInteractEvent,
)
from src.states.base_view import GameView
from src.states.map_loader import MapLoader
from src.states.battle_transition import BattleTransition
from src.world.map_registry import MapRegistry
from src.world.map_manager import MapManager
from src.world.transition import parse_transition

CONFIG = Config.load()

# Where the player respawns after whiting out — the Poké Center's named
# "entrance" spawn point (authored in oldale_town/pokemon_center.tmx).
POKECENTER_MAP = "oldale_town/pokemon_center"
POKECENTER_SPAWN = "entrance"


class OverworldView(GameView):
    def __init__(
        self,
        player_manager: PlayerManager,
        data_loader: DataLoader,
        message_service: MessageService,
    ):
        super().__init__()

        self.player_manager = player_manager
        self.save_manager = player_manager.save_manager
        self.data_loader = data_loader
        self.message_service = message_service

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

        self.map_manager = MapManager(
            loader=MapLoader(self.movement_system, self.player_state),
            registry=MapRegistry(CONFIG.game.maps_dir),
            player_state=self.player_state,
        )
        self.transition = BattleTransition()

        saved = self.save_manager.saved_position
        if saved:
            self.player_state.direction = saved.get(
                "direction", self.player_state.direction
            )
            self.setup(
                saved.get("map_name", self.player_state.map_name),
                (saved["pixel_x"], saved["pixel_y"]),
            )
        else:
            self.setup(CONFIG.game.starting_map)
            self._spawn_at_position_layer()

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
        # Boxless full view: drop any box a transient view (battle/dialog) left
        # registered, so a stray bark can't queue into a dead box.
        self.message_service.set_box(None)
        self._subscribe()
        if self.encounter_system:
            self.encounter_system.resubscribe()

    def on_hide_view(self):
        self._unsubscribe()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup(self, map_ref=None, spawn=None):
        loaded = self.map_manager.load(map_ref or CONFIG.game.starting_map, spawn)
        self._apply_loaded(loaded)

    def _apply_loaded(self, loaded) -> None:
        """Wire a freshly-loaded map into the view's render + systems."""
        self.tile_map = loaded.tile_map
        self.scene = loaded.scene
        self.npcs = loaded.npcs
        self.npc_controller = loaded.npc_controller
        self.camera = arcade.Camera2D()

        if self.encounter_system:
            self.encounter_system.cleanup()
        self.encounter_system = EncounterSystem(
            bush_tiles=loaded.bush_tiles,
            player_state=self.player_state,
            data_loader=self.data_loader,
        )

    def _spawn_at_position_layer(self) -> None:
        """New-game fallback: place the player at the map's legacy 'position'
        object when it has no named spawn points yet."""
        layer = self.tile_map.get_tilemap_layer("position")
        if layer and layer.tiled_objects:
            position = layer.tiled_objects[0].coordinates
            self.player_state.pixel_x = position.x * 2
            self.player_state.pixel_y = position.y / 2 - 110

    def respawn_at_pokecenter(self) -> None:
        """Relocate the player to the Poké Center (used after whiting out).
        Uses the shared warp seam — becomes a named spawn once authored."""
        self.player_state.direction = "up"
        loaded = self.map_manager.warp(POKECENTER_MAP, POKECENTER_SPAWN)
        self._apply_loaded(loaded)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_battle_triggered(self, event: BattleEncounterTriggeredEvent):
        self._start_battle_transition(
            event.pokemon_name, event.pokemon_level, event.pokemon_data
        )

    def _on_npc_interaction(self, event: NpcInteractEvent):
        npc_id = event.npc_id

        npc = self.data_loader.npc_dialog.get(npc_id)
        if npc is None:
            return

        state, action = self._resolve_dialog(npc_id, npc)
        self.player_manager.npc_manager.mark_talked(npc_id)

        self.overlay("dialog", npc_id=npc_id, state=state, action=action)

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
        if self.transition.active:
            result = self.transition.update(delta_time)
            if result:
                name, level, data = result
                self.swap(
                    "battle",
                    pokemon_name=name,
                    pokemon_data=data,
                    pokemon_level=level,
                )
                self.keys.clear()
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
            loaded = self.map_manager.transition(parse_transition(intent["properties"]))
            self._apply_loaded(loaded)
            intent = None

        self.movement_system.update(delta_time, self.player_state, intent)
        self.player_sprite.sync_with_state(self.player_state)

        # NPCs only think while the overworld is the active view, so they
        # naturally freeze during dialog, battle and menus.
        self.npc_controller.update(delta_time)

    def on_draw(self):
        self.clear()
        self.camera.use()
        if self.scene and self.transition.can_render_scene:
            self.scene.draw(pixelated=True)
        self.npcs.draw(pixelated=True)
        self.player_sprite.draw()

    def on_key_press(self, key, _):
        self.keys.add(key)
        if self.is_pressed(CONFIG.controls.bag, key):
            self.keys.clear()
            self.overlay("menu")
            
        if self.is_pressed(CONFIG.controls.cancel, key):
            print(f"x {self.player_state.pixel_x}, y {self.player_state.pixel_y}")

    def on_key_release(self, key, _):
        self.keys.discard(key)

    def _start_battle_transition(self, name, level, data):
        self.transition.start(name, level, data)
