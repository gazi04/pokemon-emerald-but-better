import pytest

from src.core.catch_calculator import calc_catch_probability
from src.enums.status_effect import StatusEffect


def test_low_hp_beats_full_hp():
    full = calc_catch_probability(45, 1, current_hp=50, max_hp=50, status=StatusEffect.NONE)
    low = calc_catch_probability(45, 1, current_hp=1, max_hp=50, status=StatusEffect.NONE)
    assert low > full


def test_sleep_and_freeze_double():
    none = calc_catch_probability(45, 1, 25, 50, StatusEffect.NONE)
    sleep = calc_catch_probability(45, 1, 25, 50, StatusEffect.SLEEP)
    freeze = calc_catch_probability(45, 1, 25, 50, StatusEffect.FREEZE)
    assert sleep == pytest.approx(none * 2.0)
    assert freeze == pytest.approx(none * 2.0)


def test_paralysis_burn_poison_one_and_a_half():
    none = calc_catch_probability(45, 1, 25, 50, StatusEffect.NONE)
    for status in (StatusEffect.PARALYSIS, StatusEffect.BURN, StatusEffect.POISON):
        assert calc_catch_probability(45, 1, 25, 50, status) == pytest.approx(none * 1.5)


def test_clamped_to_one():
    # Huge catch rate + ball + status would exceed 1 without the clamp.
    prob = calc_catch_probability(255, 10, 1, 50, StatusEffect.SLEEP)
    assert prob == 1.0


def test_ball_modifier_scales():
    base = calc_catch_probability(45, 1, 25, 50, StatusEffect.NONE)
    doubled = calc_catch_probability(45, 2, 25, 50, StatusEffect.NONE)
    assert doubled == pytest.approx(base * 2)
