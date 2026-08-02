from src.constants import FLICKER_INTERVAL


class BattleTransition:
    """The pre-battle screen-flicker. Owns its own timer/state so OverworldView's
    on_update doesn't. `update()` returns the pending battle data tuple on the
    frame the flicker completes, else None."""

    def __init__(
        self, max_time: float = 0.8, flicker_interval: float = FLICKER_INTERVAL
    ):
        self.active = False
        self.can_render_scene = True
        self.max_time = max_time
        self.flicker_interval = flicker_interval
        self._timer = 0.0
        self._pending: tuple | None = None

    def start(self, name, level, data) -> None:
        self.active = True
        self._timer = 0.0
        self._pending = (name, level, data)

    def update(self, delta_time: float) -> tuple | None:
        self._timer += delta_time
        self.can_render_scene = int(self._timer / self.flicker_interval) % 2 == 0

        if self._timer >= self.max_time:
            self.active = False
            self.can_render_scene = True
            self._timer = 0.0
            return self._pending
        return None
