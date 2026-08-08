import math

import arcade

from src.model.motion.player_motion import PlayerMotion
from .components.animation_manager import AnimationManager

SPRITE_DIR = "assets/sprite/player"

# Peak height (world px) the sprite rises to at the middle of a ledge hop.
HOP_HEIGHT = 24.0

# Art only exists for down/up/left; right is the mirrored left cycle.
DIRECTIONS = ("down", "up", "left")
MIRRORED = {"right": "left"}

# Step, idle, step, idle — the classic two-frame overworld walk.
WALK_SEQUENCE = [0, 2, 1, 2]
# Contact, passing, contact, other passing — a 3-pose run read as a 4-beat cycle.
RUN_SEQUENCE = [0, 1, 0, 2]


class PlayerSprite(arcade.Sprite):
    def __init__(self):
        super().__init__(scale=1.9)

        self.animations = AnimationManager()
        self._load_animations()

        self.texture = self._frame("idle", "down", 0.0)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _load_animations(self) -> None:
        for direction in DIRECTIONS:
            idle = arcade.load_texture(
                f"{SPRITE_DIR}/idle/brendan_idle_{direction}.png"
            )

            # Walk reuses the idle pose as its in-between, so it ships two
            # textures and points at idle twice via the sequence.
            walk = [
                arcade.load_texture(
                    f"{SPRITE_DIR}/walk/brendan_walk_{direction}{n}.png"
                )
                for n in (1, 2)
            ]
            run = [
                arcade.load_texture(f"{SPRITE_DIR}/run/brendan_run_{direction}{n}.png")
                for n in (1, 2, 3)
            ]

            self.animations.add("idle", direction, [idle])
            self.animations.add("walk", direction, [*walk, idle], WALK_SEQUENCE)
            self.animations.add("run", direction, run, RUN_SEQUENCE)

        for direction, source in MIRRORED.items():
            for name in ("idle", "walk", "run"):
                animation = self.animations.get(name, source)
                if animation is None:
                    continue

                self.animations.add_animation(name, direction, animation.flipped())

    # ------------------------------------------------------------------
    # Per-frame
    # ------------------------------------------------------------------

    def sync_with_state(self, state: PlayerMotion) -> None:
        self.center_x = state.pixel_x
        self.center_y = state.pixel_y

        if state.moving:
            # A ledge hop rises and falls over the move; a half-sine peaks at
            # mid-hop and returns to zero on landing. Purely visual — logical
            # position (and the camera that follows it) stays on the ground.
            if state.is_hopping:
                self.center_y += math.sin(math.pi * state.move_progress) * HOP_HEIGHT

            name = "run" if state.is_running else "walk"
            self.texture = self._frame(name, state.direction, state.move_progress)
        else:
            self.texture = self._frame("idle", state.direction, 0.0)

    def _frame(self, name: str, direction: str, progress: float) -> arcade.Texture:
        """Current texture for an animation, holding the last good pose if a
        direction has no art rather than blowing up mid-render."""
        animation = self.animations.get(name, direction)
        if animation is None:
            return self.texture
        return animation.frame(progress)

    def draw(self) -> None:
        arcade.draw_sprite(self)
