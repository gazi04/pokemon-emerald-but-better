"""
NPC behaviors — each decides *what* an NPC wants to do each frame and returns
a movement intent (the same shape PlayerInput produces) or None.

Movement is executed elsewhere (NpcController + MovementSystem); behaviors only
make decisions. One behavior = one responsibility.
"""

import random
from typing import Optional

from src.constants import TILE_SIZE

# Arcade is y-up: "up" increases y.
_OFFSETS = {
    "up": (0, TILE_SIZE),
    "down": (0, -TILE_SIZE),
    "left": (-TILE_SIZE, 0),
    "right": (TILE_SIZE, 0),
}
_DIRECTIONS = list(_OFFSETS.keys())


class Behavior:
    """Base class. Subclasses return an intent dict or None."""

    def decide(self, npc, world, delta_time: float) -> Optional[dict]:
        return None


class IdleBehavior(Behavior):
    """Stands still forever (e.g. a shop clerk)."""

    def decide(self, npc, world, delta_time: float):
        return None


class LookAroundBehavior(Behavior):
    """Turns to face a random direction on a timer. Never walks."""

    def __init__(self, cooldown: float = 2.0):
        self.cooldown = cooldown
        self.timer = random.uniform(0, cooldown)

    def decide(self, npc, world, delta_time: float):
        self.timer -= delta_time
        if self.timer > 0:
            return None
        self.timer = self.cooldown
        direction = random.choice(_DIRECTIONS)
        return {"type": "turn", "direction": direction}


class WanderBehavior(Behavior):
    """
    Steps to a random walkable adjacent tile on a timer, staying within
    `radius` tiles of its home position.
    """

    def __init__(self, radius_tiles: int = 2, cooldown: float = 1.5):
        self.radius = radius_tiles * TILE_SIZE
        self.cooldown = cooldown
        self.timer = random.uniform(0, cooldown)

    def decide(self, npc, world, delta_time: float):
        self.timer -= delta_time
        if self.timer > 0:
            return None
        self.timer = self.cooldown

        direction = random.choice(_DIRECTIONS)
        dx, dy = _OFFSETS[direction]
        target_x = npc.motion.pixel_x + dx
        target_y = npc.motion.pixel_y + dy

        # Stay leashed to home; if out of range, just face that way.
        out_of_leash = (
            abs(target_x - npc.home_x) > self.radius
            or abs(target_y - npc.home_y) > self.radius
        )
        if out_of_leash or not world.can_walk(target_x, target_y, npc):
            return {"type": "turn", "direction": direction}

        return {
            "type": "move",
            "direction": direction,
            "target_x": target_x,
            "target_y": target_y,
        }


def make_behavior(properties: dict) -> Behavior:
    """Build a behavior from TMX object properties."""
    kind = (properties.get("behavior") or "idle").lower()

    if kind == "wander":
        return WanderBehavior(
            radius_tiles=int(properties.get("wander_radius", 2)),
            cooldown=float(properties.get("move_cooldown", 1.5)),
        )
    if kind == "look_around":
        return LookAroundBehavior(
            cooldown=float(properties.get("move_cooldown", 2.0)),
        )
    return IdleBehavior()
