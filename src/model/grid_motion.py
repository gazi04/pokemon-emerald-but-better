from dataclasses import dataclass
from src.constants import MOVE_DURATION


@dataclass
class GridMotion:
    """
    Tile-based motion state shared by any moving overworld entity (NPCs).
    Mirrors the movement fields on PlayerState so MovementSystem can drive
    both the player and NPCs with the same tween logic.
    """
    pixel_x: float = 0.0
    pixel_y: float = 0.0
    target_x: float = 0.0
    target_y: float = 0.0
    start_x: float = 0.0
    start_y: float = 0.0
    grid_x: int = 0
    grid_y: int = 0
    direction: str = "down"
    moving: bool = False
    move_progress: float = 0.0
    move_duration: float = MOVE_DURATION
