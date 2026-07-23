import arcade


class Animation:
    """A looping frame cycle driven by 0..1 progress.

    `sequence` indexes into `frames`, so a pose reused several times in one
    cycle (the idle pose between walk steps) is loaded once and referenced
    twice. `fps` defaults to one full cycle per unit of progress — i.e. exactly
    one cycle per tile stepped.
    """

    def __init__(self, frames, sequence=None, fps=None):
        self.frames = frames
        self.sequence = sequence or list(range(len(frames)))
        self.fps = fps or len(self.sequence)

    def frame(self, progress: float) -> arcade.Texture:
        index = int(progress * self.fps) % len(self.sequence)
        return self.frames[self.sequence[index]]

    def flipped(self) -> "Animation":
        """The same cycle mirrored — left-facing art reused for right."""
        return Animation(
            [tex.flip_left_right() for tex in self.frames], self.sequence, self.fps
        )


class AnimationManager:
    def __init__(self):
        self.animations: dict[tuple, Animation] = {}

    def add(
        self,
        name: str,
        direction: str,
        frames: list[arcade.Texture],
        sequence: list[int] | None = None,
        fps: float | None = None,
    ) -> Animation:
        animation = Animation(frames, sequence, fps)
        self.animations[(name, direction)] = animation
        return animation

    def add_animation(self, name: str, direction: str, animation: Animation) -> None:
        self.animations[(name, direction)] = animation

    def get(self, name: str, direction: str) -> Animation | None:
        return self.animations.get((name, direction))
