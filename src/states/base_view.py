import arcade

from src.core.event_bus import global_bus
from src.core.events import OverlayViewEvent, SwapViewEvent, CloseViewEvent


class GameView(arcade.View):
    """Shared base for every screen: input mapping, nav verbs, and optional UI
    delegation. Subclasses set their own `self.ui` (with its concrete type) or
    leave it unset and override on_draw/on_update, as overworld/evolving/battle
    do. The lifecycle defaults read `ui` via getattr so they never constrain a
    subclass's UI type."""

    # input -------------------------------------------------------
    def is_pressed(self, config_key: str, symbol: int) -> bool:
        """config_key is a resolved CONFIG.controls value, e.g. CONFIG.controls.interact."""
        return getattr(arcade.key, config_key, None) == symbol

    # lifecycle (safe defaults; custom-render views override) -----
    def on_draw(self):
        self.clear()
        ui = getattr(self, "ui", None)
        if ui is not None:
            ui.draw()

    def on_update(self, delta_time: float):
        update = getattr(getattr(self, "ui", None), "update", None)
        if callable(update):
            update(delta_time)

    # navigation (readable verbs over the bus) --------------------
    def overlay(self, target: str, **payload):
        global_bus.publish(OverlayViewEvent(target=target, payload=payload))

    def swap(self, target: str, **payload):
        global_bus.publish(SwapViewEvent(target=target, payload=payload))

    def close(self):
        global_bus.publish(CloseViewEvent())
