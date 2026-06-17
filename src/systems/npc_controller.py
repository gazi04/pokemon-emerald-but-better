"""
Drives every NPC each frame: asks its behavior for an intent, executes the
movement via MovementSystem, and answers walkability queries (walls, map
bounds, other NPCs, the player).
"""
import arcade
from src.constants import TILE_SIZE

# Two positions count as the same tile if closer than half a tile.
_SAME_CELL = TILE_SIZE * 0.5


class NpcController:
    def __init__(
        self,
        npcs: arcade.SpriteList,
        movement_system,
        collision_tiles,
        player_state,
        map_width: float,
        map_height: float,
    ):
        self.npcs = npcs
        self.movement_system = movement_system
        self.collision_tiles = collision_tiles
        self.player_state = player_state
        self.map_width = map_width
        self.map_height = map_height

    def update(self, delta_time: float) -> None:
        for npc in self.npcs:
            if not npc.motion.moving:
                intent = npc.behavior.decide(npc, self, delta_time)
                self._apply_intent(npc, intent)

            self.movement_system.advance(delta_time, npc.motion)
            npc.sync_sprite()

    def _apply_intent(self, npc, intent) -> None:
        if not intent:
            return
        if intent["type"] == "turn":
            npc.motion.direction = intent["direction"]
        elif intent["type"] == "move":
            npc.motion.direction = intent.get("direction", npc.motion.direction)
            self.movement_system.begin(npc.motion, intent)

    # ------------------------------------------------------------------
    # Walkability — used by behaviors
    # ------------------------------------------------------------------

    def can_walk(self, x: float, y: float, asking) -> bool:
        # Map bounds
        if x < 0 or y < 0 or x > self.map_width or y > self.map_height:
            return False

        # Static collision (walls, furniture)
        if arcade.get_sprites_at_point((x, y), self.collision_tiles):
            return False

        # The player
        px, py = self._effective_pos(self.player_state)
        if self._same_cell(x, y, px, py):
            return False

        # Other NPCs (current or in-flight target cell)
        for other in self.npcs:
            if other is asking:
                continue
            ox, oy = self._effective_pos(other.motion)
            if self._same_cell(x, y, ox, oy):
                return False

        return True

    @staticmethod
    def _effective_pos(motion):
        """The cell an entity occupies — its target while stepping, else current."""
        if getattr(motion, "moving", False):
            return motion.target_x, motion.target_y
        return motion.pixel_x, motion.pixel_y

    @staticmethod
    def _same_cell(ax, ay, bx, by) -> bool:
        return abs(ax - bx) < _SAME_CELL and abs(ay - by) < _SAME_CELL
