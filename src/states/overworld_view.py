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

CONFIG = Config.load()

# Where the player respawns after whiting out. Matches the Poké Center door
# entrance (see the "door_pokecenter" transition in littleroot_town.tmx).
POKECENTER_MAP = "oldale_town/pokemon_center"
POKECENTER_SPAWN = (496, 210)


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

        self.map_loader = MapLoader(self.movement_system, self.player_state)
        self.transition = BattleTransition()

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

    def setup(self, map=None, playerPos=None):
        loaded = self.map_loader.load(map or CONFIG.game.starting_map)
        self.tile_map = loaded.tile_map
        self.scene = loaded.scene
        self.npcs = loaded.npcs
        self.npc_controller = loaded.npc_controller

        if playerPos:
            self.player_state.pixel_x = playerPos[0]
            self.player_state.pixel_y = playerPos[1]

        self.camera = arcade.Camera2D()

        if self.encounter_system:
            self.encounter_system.cleanup()

        self.encounter_system = EncounterSystem(
            bush_tiles=loaded.bush_tiles,
            player_state=self.player_state,
            data_loader=self.data_loader,
        )

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
        if self.scene and self.transition.can_render_scene:
            self.scene.draw(pixelated=True)
        self.npcs.draw(pixelated=True)
        self.player_sprite.draw()

    def on_key_press(self, key, _):
        self.keys.add(key)
        if self.is_pressed(CONFIG.controls.bag, key):
            self.keys.clear()
            self.overlay("menu")

    def on_key_release(self, key, _):
        self.keys.discard(key)

    def _start_battle_transition(self, name, level, data):
        self.transition.start(name, level, data)
