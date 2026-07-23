from dataclasses import dataclass
from src.constants import PLAYER_MOVE_DURATION
from src.model.motion.grid_motion import GridMotion


@dataclass
class PlayerMotion(GridMotion):
    """Player overworld motion = tile motion (GridMotion) + the current map.

    Transient overworld state (not save data); MovementSystem drives it through
    the inherited flat fields, exactly as it drives an NPC's GridMotion.
    """

    map_name: str = "littleroot_town"
    move_duration: float = PLAYER_MOVE_DURATION  # override; GridMotion default is 0.2
    is_running: bool = False
