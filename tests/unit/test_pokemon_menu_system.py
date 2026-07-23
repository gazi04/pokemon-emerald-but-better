from unittest.mock import MagicMock


from src.model.save.player import PlayerPokemon, PlayerPokemonMove
from src.systems.pokemon_menu_system import PokemonMenuSystem


def make_team(names):
    return [
        PlayerPokemon(
            name=n,
            hp=50,
            level=5,
            exp=0,
            ability="",
            moves=[PlayerPokemonMove(name="tackle", pp=35)],
            held_item=None,
        )
        for n in names
    ]


def make_system(names=("a", "b", "c")):
    sm = MagicMock()
    sm.player.pokemon = make_team(names)
    return PokemonMenuSystem(sm)


# --- move_pokemon ---


def test_move_pokemon_swaps_slots():
    system = make_system(["alpha", "beta", "gamma"])
    system.start_moving()  # sets moving_pokemon_index = 0 (team_index)
    system.move_pokemon(1)
    assert system.team[0].name == "beta"
    assert system.team[1].name == "alpha"


def test_move_pokemon_same_index_no_swap():
    system = make_system(["alpha", "beta"])
    system.start_moving()
    system.move_pokemon(0)
    assert system.team[0].name == "alpha"
    assert not system.is_moving_pokemon


# --- move_team_index ---


def test_move_team_index_forward():
    system = make_system(["a", "b", "c"])
    system.move_team_index(1)
    assert system.team_index == 1


def test_move_team_index_wraps_at_end():
    system = make_system(["a", "b", "c"])
    system.team_index = 2
    system.move_team_index(1)
    assert system.team_index == 0


def test_move_team_index_wraps_backward():
    system = make_system(["a", "b", "c"])
    system.team_index = 0
    system.move_team_index(-1)
    assert system.team_index == 2


# --- move_tooltip_index ---


def test_move_tooltip_index_forward():
    system = make_system()
    system.move_tooltip_index(1, 4)
    assert system.tooltip_index == 1


def test_move_tooltip_index_wraps_at_count():
    system = make_system()
    system.tooltip_index = 3
    system.move_tooltip_index(1, 4)
    assert system.tooltip_index == 0


def test_move_tooltip_index_wraps_backward():
    system = make_system()
    system.tooltip_index = 0
    system.move_tooltip_index(-1, 4)
    assert system.tooltip_index == 3


# --- start_moving / cancel_moving ---


def test_start_moving_sets_flags():
    system = make_system()
    system.team_index = 2
    system.start_moving()
    assert system.is_moving_pokemon
    assert system.moving_pokemon_index == 2


def test_cancel_moving_resets_flags():
    system = make_system()
    system.start_moving()
    system.cancel_moving()
    assert not system.is_moving_pokemon
    assert system.moving_pokemon_index == -1


# --- reset_tooltip ---


def test_reset_tooltip_sets_zero():
    system = make_system()
    system.tooltip_index = 3
    system.reset_tooltip()
    assert system.tooltip_index == 0


def test_move_team_index_single_pokemon_wraps_to_self():
    system = make_system(["only"])
    system.move_team_index(1)
    assert system.team_index == 0
    system.move_team_index(-1)
    assert system.team_index == 0


def test_move_pokemon_single_team_same_index_cancels():
    system = make_system(["solo"])
    system.start_moving()  # moving_pokemon_index = 0
    system.move_pokemon(0)  # to == moving_pokemon_index → no-op path
    assert system.team[0].name == "solo"
    assert not system.is_moving_pokemon
