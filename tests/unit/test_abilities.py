"""Tests for the data-driven ability hooks on BattlePokemon
(Blaze / Static / Levitate)."""
from unittest.mock import patch


from src.model.battle.battle_pokemon import BattlePokemon
from src.model.static.ability import Ability
from src.model.static.pokemon import (
    PokemonMove,
    PokemonSpecies,
    SpritePaths,
    PokemonStat,
)
from src.model.save.player import PlayerPokemon, PlayerPokemonMove
from src.enums.status_effect import StatusEffect


BLAZE = {
    "name": "Blaze",
    "description": "",
    "effects": [
        {"trigger": "on_attack", "type": "damage_boost", "target": "self",
         "stat": "attack", "change": 50, "condition": "low_hp",
         "chance": None, "move_type": "fire"},
    ],
}
STATIC = {
    "name": "Static",
    "description": "",
    "effects": [
        {"trigger": "on_hit", "type": "status", "target": "enemy",
         "condition": "contact", "stat": None, "change": None, "chance": 0.3,
         "status": "paralyzed"},
    ],
}
LEVITATE = {
    "name": "Levitate",
    "description": "",
    "effects": [
        {"trigger": "on_hit", "type": "immunity", "target": "self",
         "condition": "ground_type", "stat": None, "change": None, "chance": None},
    ],
}


def _species(types=("normal",)):
    return PokemonSpecies(
        baseExp=62, catch_rate=45, abilities=[], types=list(types), evolution=None,
        sprites=SpritePaths(back="b", front="f"),
        stats=PokemonStat(hp=100, attack=60, defence=50, special_attack=50,
                          special_defence=50, speed=45),
        learnset=[],
    )


def _mon(ability_dict=None, types=("normal",)):
    ability = Ability(ability_dict) if ability_dict else None
    pp = PlayerPokemon("mon", 999, 20, 0, "x", [PlayerPokemonMove("tackle", 35)], None)
    b = BattlePokemon.from_player(ability, _species(types), pp, False)
    b.current_hp = b.max_hp
    return b


def _move(type_="fire", category="physical"):
    return PokemonMove("m", category, type_, 40, 100, 35, 0, 0, None, None, [])


# --- Blaze -----------------------------------------------------------------


def test_blaze_boosts_only_at_low_hp():
    mon = _mon(BLAZE)
    mult_full, _ = mon.ability_attack_multiplier(_move("fire"))
    assert mult_full == 1.0

    mon.current_hp = mon.max_hp // 4  # below 1/3
    mult_low, messages = mon.ability_attack_multiplier(_move("fire"))
    assert mult_low == 1.5 and messages


def test_blaze_only_matching_move_type():
    mon = _mon(BLAZE)
    mon.current_hp = mon.max_hp // 4
    mult, _ = mon.ability_attack_multiplier(_move("water"))  # not fire
    assert mult == 1.0


# --- Levitate --------------------------------------------------------------


def test_levitate_immune_to_ground():
    mon = _mon(LEVITATE)
    assert mon.immunity_to(_move("ground")) is not None
    assert mon.immunity_to(_move("normal")) is None


# --- Static ----------------------------------------------------------------


def test_static_paralyses_attacker_on_contact():
    defender = _mon(STATIC)
    attacker = _mon()
    with patch("src.model.battle.battle_pokemon.random.random", return_value=0.0):
        messages = defender.on_hit(attacker, _move("normal", "physical"))
    assert attacker.status_effect == StatusEffect.PARALYSIS and messages


def test_static_no_proc_on_non_contact():
    defender = _mon(STATIC)
    attacker = _mon()
    with patch("src.model.battle.battle_pokemon.random.random", return_value=0.0):
        messages = defender.on_hit(attacker, _move("normal", "special"))
    assert attacker.status_effect == StatusEffect.NONE and not messages


def test_no_ability_hooks_are_inert():
    mon = _mon(None)
    assert mon.ability_attack_multiplier(_move()) == (1.0, [])
    assert mon.immunity_to(_move("ground")) is None
    assert mon.on_hit(_mon(None), _move()) == []
