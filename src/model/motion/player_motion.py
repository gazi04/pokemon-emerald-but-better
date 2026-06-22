from dataclasses import dataclass


@dataclass
class PlayerMotion:
    """Overworld position + tile-motion state for the player.

    Lives in the state layer (not save) — it is transient overworld motion
    that MovementSystem drives, mirroring GridMotion for NPCs.
    """

    map_name: str = "littleroot_town"
    direction: str = "down"

    grid_x: int = 0
    grid_y: int = 0

    pixel_x: float = 0.0
    pixel_y: float = 0.0
    target_x: float = 0.0
    target_y: float = 0.0
    start_x: float = 0.0
    start_y: float = 0.0

    moving: bool = False
    move_progress: float = 0.0
    move_duration: float = 0.25
