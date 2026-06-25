from src.model.motion.grid_motion import GridMotion
from src.model.motion.player_motion import PlayerMotion


def test_player_motion_adds_only_map_name():
    # PlayerMotion subclasses GridMotion — the 12 tile-motion fields are defined
    # once on the base; map_name is the only field the player adds.
    assert set(vars(PlayerMotion())) == set(vars(GridMotion())) | {"map_name"}


def test_move_duration_defaults_preserved():
    assert PlayerMotion().move_duration == 0.25
    assert GridMotion().move_duration == 0.2
