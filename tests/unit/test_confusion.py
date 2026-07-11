"""Tests for the confusion volatile status on BattlePokemon."""
from unittest.mock import patch

from src.model.battle.battle_pokemon import BattlePokemon
from src.model.static.pokemon import (
    PokemonSpecies,
    SpritePaths,
    PokemonStat,
    PokemonMoveEffect,
    PokemonMove,
)
from src.model.save.player import PlayerPokemon, PlayerPokemonMove
from src.enums.status_effect import StatusEffect
from src.enums.effect_type import EffectType


def _mon():
    sp = PokemonSpecies(
        baseExp=62, catch_rate=45, abilities=[], types=["normal"], evolution=None,
        sprites=SpritePaths(back="b", front="f"),
        stats=PokemonStat(hp=100, attack=60, defence=50, special_attack=50,
                          special_defence=50, speed=45),
        learnset=[],
    )
    pp = PlayerPokemon("mon", 999, 20, 0, "x", [PlayerPokemonMove("tackle", 35)], None)
    b = BattlePokemon.from_player(None, sp, pp, False)
    b.current_hp = b.max_hp
    return b


def test_confusion_coexists_with_major_status():
    mon = _mon()
    mon.status_effect = StatusEffect.POISON
    effect = PokemonMoveEffect(
        target="opponent", type=EffectType.STATUS_CONDITION,
        condition=StatusEffect.CONFUSION, chance=100,
    )
    move = PokemonMove("confuse ray", "status", "ghost", 0, 100, 10, 0, 0, None, None, [effect])
    attacker = _mon()
    with patch("src.model.battle.battle_pokemon.random.randint", return_value=3):
        attacker.execute_effects(move, mon)
    # Major status untouched, confusion counter set.
    assert mon.status_effect == StatusEffect.POISON
    assert mon.confusion_counter == 3


def test_confused_pokemon_can_hurt_itself():
    mon = _mon()
    mon.confusion_counter = 2
    hp_before = mon.current_hp
    with patch("src.model.battle.battle_pokemon.random.random", return_value=0.0):  # <1/3 -> self-hit
        messages, can_move = mon.check_can_move(0)
    assert can_move is False
    assert mon.current_hp < hp_before
    assert any("confused" in m for m in messages)


def test_confusion_wears_off():
    mon = _mon()
    mon.confusion_counter = 1
    with patch("src.model.battle.battle_pokemon.random.random", return_value=0.99):  # no self-hit
        messages, can_move = mon.check_can_move(0)
    assert can_move is True
    assert mon.confusion_counter == 0
    assert any("snapped out" in m for m in messages)
