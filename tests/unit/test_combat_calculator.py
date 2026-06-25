import json
from unittest.mock import patch

import pytest

from src.core.combat_calculator import _get_stat, calculate_damage
from src.model.battle.combat_result import CombatResult
from src.enums.stat import Stat
from src.enums.status_effect import StatusEffect
from src.model.static.pokemon import PokemonMove, PokemonStat

with open("data/types.json") as _f:
    TYPES = json.load(_f)


def make_stat(hp=50, attack=50, defence=50, sp_atk=50, sp_def=50, speed=50):
    return PokemonStat(
        hp=hp,
        attack=attack,
        defence=defence,
        special_attack=sp_atk,
        special_defence=sp_def,
        speed=speed,
    )


def make_move(
    name="tackle", category="physical", type_="normal", power=40, accuracy=100, pp=35
):
    return PokemonMove(
        name=name,
        category=category,
        type=type_,
        power=power,
        accuracy=accuracy,
        pp=pp,
        effects=[],
    )


def calc(
    attacker_types=None,
    defender_types=None,
    move=None,
    level=10,
    atk_stat=None,
    def_stat=None,
    atk_mods=None,
    def_mods=None,
    atk_status=StatusEffect.NONE,
    crit_modifier=0,
):
    move = move or make_move()
    atk_stat = atk_stat or make_stat()
    def_stat = def_stat or make_stat()
    atk_mods = atk_mods or {}
    def_mods = def_mods or {}
    attacker_types = attacker_types or ["normal"]
    defender_types = defender_types or ["normal"]
    return calculate_damage(
        attacker_level=level,
        attacker_stats=atk_stat,
        attacker_types=attacker_types,
        attacker_modifiers=atk_mods,
        attacker_status=atk_status,
        move_data=move,
        defender_stats=def_stat,
        defender_types=defender_types,
        defender_modifiers=def_mods,
        crit_modifier=crit_modifier,
        type_chart=TYPES,
    )


# --- Basic hit ---


def test_normal_hit_deals_positive_damage():
    result = calc()
    assert result.damage > 0
    assert result.effectiveness == 1.0
    assert not result.is_miss
    assert not result.is_critical


def test_normal_hit_has_no_effectiveness_message_for_neutral():
    result = calc(defender_types=["normal"])
    assert not any("effective" in m.lower() for m in result.messages)
    assert not any("no effect" in m.lower() for m in result.messages)


# --- Type effectiveness ---


def test_super_effective_doubles_damage():
    with patch("src.core.combat_calculator._roll_critical", return_value=False):
        neutral = calc(
            move=make_move(type_="fire"),
            attacker_types=["normal"],
            defender_types=["normal"],
        )
        super_eff = calc(
            move=make_move(type_="fire"),
            attacker_types=["normal"],
            defender_types=["grass"],
        )
    assert super_eff.effectiveness == 2.0
    assert super_eff.damage > neutral.damage
    assert any("super effective" in m.lower() for m in super_eff.messages)


def test_not_very_effective_halves_damage():
    with patch("src.core.combat_calculator._roll_critical", return_value=False):
        neutral = calc(
            move=make_move(type_="fire"),
            attacker_types=["normal"],
            defender_types=["normal"],
        )
        nve = calc(
            move=make_move(type_="fire"),
            attacker_types=["normal"],
            defender_types=["fire"],
        )
    assert nve.effectiveness == 0.5
    assert nve.damage < neutral.damage
    assert any("not very effective" in m.lower() for m in nve.messages)


def test_immune_type_deals_zero_damage():
    result = calc(
        move=make_move(type_="normal"),
        attacker_types=["normal"],
        defender_types=["ghost"],
    )
    assert result.effectiveness == 0.0
    assert result.damage == 0
    assert any("no effect" in m.lower() for m in result.messages)


# --- STAB ---


def test_stab_increases_damage_vs_no_stab():
    with patch("src.core.combat_calculator._roll_critical", return_value=False):
        no_stab = calc(
            move=make_move(type_="fire"),
            attacker_types=["water"],
            defender_types=["normal"],
        )
        stab = calc(
            move=make_move(type_="fire"),
            attacker_types=["fire"],
            defender_types=["normal"],
        )
    assert stab.damage > no_stab.damage


# --- Status move ---


def test_status_move_deals_zero_damage():
    status_move = make_move(category="status", power=None)
    result = calc(move=status_move)
    assert result.damage == 0
    assert not result.is_miss


def test_zero_power_move_deals_zero_damage():
    result = calc(move=make_move(power=0))
    assert result.damage == 0


# --- Critical hit ---


def test_critical_hit_flag_and_higher_damage():
    normal_result = calc(crit_modifier=0)
    with patch("src.core.combat_calculator._roll_critical", return_value=True):
        crit_result = calc(crit_modifier=0)
    assert crit_result.is_critical
    assert crit_result.damage >= normal_result.damage
    assert any("critical" in m.lower() for m in crit_result.messages)


# --- Miss ---


def test_miss_returns_zero_damage():
    with patch("src.core.combat_calculator._check_accuracy", return_value=False):
        result = calc()
    assert result.is_miss
    assert result.damage == 0
    assert result.messages == ["It missed."]


def test_no_accuracy_move_never_misses():
    result = calc(move=make_move(accuracy=None))
    assert not result.is_miss


# --- Stat stages ---


def test_positive_stat_stage_increases_effective_stat():
    low = _get_stat(Stat.ATTACK, make_stat(attack=50), {}, StatusEffect.NONE)
    high = _get_stat(
        Stat.ATTACK, make_stat(attack=50), {Stat.ATTACK: 3}, StatusEffect.NONE
    )
    assert high > low


def test_negative_stat_stage_decreases_effective_stat():
    base = _get_stat(Stat.ATTACK, make_stat(attack=50), {}, StatusEffect.NONE)
    low = _get_stat(
        Stat.ATTACK, make_stat(attack=50), {Stat.ATTACK: -3}, StatusEffect.NONE
    )
    assert low < base


def test_paralysis_halves_speed():
    normal_speed = _get_stat(Stat.SPEED, make_stat(speed=100), {}, StatusEffect.NONE)
    para_speed = _get_stat(
        Stat.SPEED, make_stat(speed=100), {}, StatusEffect.PARALYSIS
    )
    assert para_speed == normal_speed // 2


# --- Level scaling ---


def test_higher_level_attacker_deals_more_damage():
    low_level = calc(level=5)
    high_level = calc(level=50)
    assert high_level.damage > low_level.damage


# --- Dual-type / STAB combos ---


def test_dual_type_defender_multipliers_stack():
    # water vs fire/rock: 2.0 * 2.0 = 4.0
    result = calc(
        move=make_move(type_="water"),
        attacker_types=["normal"],
        defender_types=["fire", "rock"],
    )
    assert result.effectiveness == 4.0


def test_stab_plus_super_effective_stacks():
    with patch("src.core.combat_calculator._roll_critical", return_value=False):
        stab_se = calc(
            move=make_move(type_="fire"),
            attacker_types=["fire"],
            defender_types=["grass"],
        )
        no_stab = calc(
            move=make_move(type_="fire"),
            attacker_types=["normal"],
            defender_types=["grass"],
        )
    assert stab_se.damage > no_stab.damage


def test_burn_status_does_not_affect_attack_currently():
    # burn reducing attack is not implemented — documents missing feature
    normal = _get_stat(Stat.ATTACK, make_stat(attack=100), {}, StatusEffect.NONE)
    burned = _get_stat(Stat.ATTACK, make_stat(attack=100), {}, StatusEffect.BURN)
    assert burned == normal
