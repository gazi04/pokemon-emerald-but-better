from unittest.mock import MagicMock

import pytest

from src.model.player import PlayerPokemon, PlayerPokemonMove
from src.systems.pokemon_menu_system import PokemonMenuSystem


def make_team(names):
    return [
        PlayerPokemon(name=n, hp=50, level=5, exp=0, moves=[PlayerPokemonMove(name="tackle", pp=35)])
        for n in names
    ]


def make_system(names=("a", "b", "c")):
    sm = MagicMock()
    sm.player.pokemon = make_team(names)
    return PokemonMenuSystem(sm)


# --- movePokemon ---

def test_move_pokemon_swaps_slots():
    system = make_system(["alpha", "beta", "gamma"])
    system.startMoving()  # sets movingPokemonIndex = 0 (teamIndex)
    system.movePokemon(1)
    assert system.team[0].name == "beta"
    assert system.team[1].name == "alpha"


def test_move_pokemon_same_index_no_swap():
    system = make_system(["alpha", "beta"])
    system.startMoving()
    system.movePokemon(0)
    assert system.team[0].name == "alpha"
    assert not system.isMovingPokemon


# --- moveTeamIndex ---

def test_move_team_index_forward():
    system = make_system(["a", "b", "c"])
    system.moveTeamIndex(1)
    assert system.teamIndex == 1


def test_move_team_index_wraps_at_end():
    system = make_system(["a", "b", "c"])
    system.teamIndex = 2
    system.moveTeamIndex(1)
    assert system.teamIndex == 0


def test_move_team_index_wraps_backward():
    system = make_system(["a", "b", "c"])
    system.teamIndex = 0
    system.moveTeamIndex(-1)
    assert system.teamIndex == 2


# --- moveTooltipIndex ---

def test_move_tooltip_index_forward():
    system = make_system()
    system.moveTooltipIndex(1, 4)
    assert system.tooltipIndex == 1


def test_move_tooltip_index_wraps_at_count():
    system = make_system()
    system.tooltipIndex = 3
    system.moveTooltipIndex(1, 4)
    assert system.tooltipIndex == 0


def test_move_tooltip_index_wraps_backward():
    system = make_system()
    system.tooltipIndex = 0
    system.moveTooltipIndex(-1, 4)
    assert system.tooltipIndex == 3


# --- startMoving / cancelMoving ---

def test_start_moving_sets_flags():
    system = make_system()
    system.teamIndex = 2
    system.startMoving()
    assert system.isMovingPokemon
    assert system.movingPokemonIndex == 2


def test_cancel_moving_resets_flags():
    system = make_system()
    system.startMoving()
    system.cancelMoving()
    assert not system.isMovingPokemon
    assert system.movingPokemonIndex == -1


# --- resetTooltip ---

def test_reset_tooltip_sets_zero():
    system = make_system()
    system.tooltipIndex = 3
    system.resetTooltip()
    assert system.tooltipIndex == 0


def test_move_team_index_single_pokemon_wraps_to_self():
    system = make_system(["only"])
    system.moveTeamIndex(1)
    assert system.teamIndex == 0
    system.moveTeamIndex(-1)
    assert system.teamIndex == 0


def test_move_pokemon_single_team_same_index_cancels():
    system = make_system(["solo"])
    system.startMoving()  # movingPokemonIndex = 0
    system.movePokemon(0)  # to == movingPokemonIndex → no-op path
    assert system.team[0].name == "solo"
    assert not system.isMovingPokemon
