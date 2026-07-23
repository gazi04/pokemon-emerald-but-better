from src.model.motion.grid_motion import GridMotion
from src.model.motion.player_motion import PlayerMotion


def test_player_motion_adds_only_player_fields():
    # PlayerMotion subclasses GridMotion — the tile-motion fields are defined
    # once on the base. The player adds only what NPCs have no use for: the
    # current map, and whether the run key is held.
    assert set(vars(PlayerMotion())) == set(vars(GridMotion())) | {
        "map_name",
        "is_running",
    }


def test_move_duration_defaults_preserved():
    assert PlayerMotion().move_duration == 0.25
    assert GridMotion().move_duration == 0.2
