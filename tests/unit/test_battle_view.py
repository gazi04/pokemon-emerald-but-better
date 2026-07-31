"""Tests for BattleView's enemy-swap chokepoint.

`BattleView.__init__` needs a real arcade window and a parsed .tmx layout, but
`set_enemy` only touches five attributes. Constructing via `__new__` skips
`__init__` entirely, so the swap logic is testable without a GL context.
"""

from unittest.mock import MagicMock

import pytest

from src.model.battle.battle_pokemon import BattlePokemon
from src.model.static.trainer import TrainerPokemonMove
from src.states.battle_view import BattleView

# poochyena/zigzagoon declare abilities the fixture ability.json doesn't carry,
# and set_enemy takes the ability as a parameter anyway — so use one that exists.
FIXTURE_ABILITY = "intimidate"
MOVES = [TrainerPokemonMove("tackle", 25)]


@pytest.fixture
def battle_view(data_loader, player_manager):
    """A BattleView with only what set_enemy reads. No arcade window."""
    view = BattleView.__new__(BattleView)
    view.data_loader = data_loader
    view.player_manager = player_manager
    view.enemy_sprite = MagicMock()
    view.battle_system = MagicMock()
    return view


def test_set_enemy_marks_the_new_pokemon_as_seen(battle_view, player_manager):
    """B1: a trainer's 2nd+ Pokémon must reach the Pokédex. Before the fix
    mark_seen only ever fired once, in __init__, for the lead."""
    assert player_manager.get_seen_pokemon() == []

    battle_view.set_enemy("poochyena", 5, MOVES, FIXTURE_ABILITY)

    assert player_manager.get_seen_pokemon() == ["poochyena"]


def test_set_enemy_marks_each_successive_switch_in(battle_view, player_manager):
    battle_view.set_enemy("poochyena", 5, MOVES, FIXTURE_ABILITY)
    battle_view.set_enemy("zigzagoon", 7, MOVES, FIXTURE_ABILITY)

    assert player_manager.get_seen_pokemon() == ["poochyena", "zigzagoon"]


def test_set_enemy_rejects_unknown_species(battle_view):
    """set_enemy takes a lowercase DataLoader id by contract — require_pokemon
    is case-sensitive, so bad casing fails loudly here rather than silently
    writing a broken Pokédex entry. Lowercase normalization for the seen list
    itself is PlayerSave.mark_seen's job."""
    with pytest.raises(KeyError):
        battle_view.set_enemy("POOCHYENA", 5, MOVES, FIXTURE_ABILITY)


def test_set_enemy_rebinds_the_battle_system_enemy(battle_view):
    """The desync the docstring warns about: view and system must agree on who
    is on the field."""
    battle_view.set_enemy("poochyena", 5, MOVES, FIXTURE_ABILITY)

    assert isinstance(battle_view.enemy_battle, BattlePokemon)
    assert battle_view.battle_system.enemy_pokemon is battle_view.enemy_battle
    assert battle_view.enemy_battle.level == 5


def test_set_enemy_retextures_the_sprite(battle_view, data_loader):
    battle_view.set_enemy("poochyena", 5, MOVES, FIXTURE_ABILITY)

    expected = data_loader.require_pokemon("poochyena").sprites.front
    battle_view.enemy_sprite.set_new_texture.assert_called_once_with(expected)
