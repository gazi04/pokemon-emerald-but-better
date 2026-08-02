"""
NPC behaviors — each decides *what* an NPC wants to do each frame and returns
a movement intent (the same shape PlayerInput produces) or None.

Movement is executed elsewhere (NpcController + MovementSystem); behaviors only
make decisions. One behavior = one responsibility.
"""

import random
from src.constants import DIRECTION_OFFSETS, TILE_SIZE
from src.core.event_bus import global_bus
from src.core.events import NpcInteractEvent, NpcSpottedPlayerEvent

_OFFSETS = DIRECTION_OFFSETS
_DIRECTIONS = list(_OFFSETS.keys())

DEFAULT_SIGHT_RANGE = 4


class Behavior:
    """Base class. Subclasses return an intent dict or None."""

    def decide(self, npc, world, delta_time: float) -> dict | None:
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


class TrainerSightBehavior(Behavior):
    """Wraps another behavior with trainer line-of-sight.

    While unspotted the NPC just runs `inner` (idle/wander/look around). The
    moment the player steps into its facing line it locks on: publishes
    NpcSpottedPlayerEvent (the overworld freezes player input), walks up to the
    player, then publishes NpcInteractEvent — which runs the NPC's normal
    dialog and, since it is a trainer, the battle after it.

    `can_challenge(npc_id)` is asked *every* frame before any raycast, so an
    NPC with no team never looks, and a defeated one stops challenging.
    """

    PATROL, APPROACH, DONE = "patrol", "approach", "done"

    def __init__(
        self, inner: Behavior, can_challenge, sight_range: int = DEFAULT_SIGHT_RANGE
    ):
        self.inner = inner
        self.can_challenge = can_challenge
        self.sight_range = sight_range
        self.state = self.PATROL

    def decide(self, npc, world, delta_time: float):
        if self.state == self.DONE:
            return None

        if self.state == self.APPROACH:
            return self._approach(npc, world)

        # Cheap gate first: no team (or already beaten) means never look.
        if not self.can_challenge(npc.npc_id):
            return self.inner.decide(npc, world, delta_time)

        if world.line_of_sight(npc, self.sight_range) is None:
            return self.inner.decide(npc, world, delta_time)

        self.state = self.APPROACH
        global_bus.publish(NpcSpottedPlayerEvent(npc_id=npc.npc_id))
        return self._approach(npc, world)

    def _approach(self, npc, world):
        """Step toward the player until adjacent, then start the dialog."""
        distance = world.line_of_sight(npc, self.sight_range)
        if distance is not None and distance <= 1:
            return self._challenge(npc)

        direction = npc.motion.direction
        dx, dy = _OFFSETS[direction]
        target_x = npc.motion.pixel_x + dx
        target_y = npc.motion.pixel_y + dy

        # Something got in the way (or the player slipped out of the line) —
        # challenge from where we stand rather than walking forever.
        if not world.can_walk(target_x, target_y, npc):
            return self._challenge(npc)

        return {
            "type": "move",
            "direction": direction,
            "target_x": target_x,
            "target_y": target_y,
        }

    def _challenge(self, npc):
        self.state = self.DONE
        global_bus.publish(NpcInteractEvent(npc_id=npc.npc_id))
        return None


def make_behavior(properties: dict, can_challenge=None) -> Behavior:
    """Build a behavior from TMX object properties.

    Pass `can_challenge` (npc_id -> bool) to give the NPC trainer sight. Set
    `sight_range` to 0 on the Tiled object to opt a trainer out of spotting.
    """
    kind = (properties.get("behavior") or "idle").lower()

    if kind == "wander":
        behavior = WanderBehavior(
            radius_tiles=int(properties.get("wander_radius", 2)),
            cooldown=float(properties.get("move_cooldown", 1.5)),
        )
    elif kind == "look_around":
        behavior = LookAroundBehavior(
            cooldown=float(properties.get("move_cooldown", 2.0)),
        )
    else:
        behavior = IdleBehavior()

    sight_range = int(properties.get("sight_range", DEFAULT_SIGHT_RANGE))
    if can_challenge is not None and sight_range > 0:
        behavior = TrainerSightBehavior(behavior, can_challenge, sight_range)

    return behavior
