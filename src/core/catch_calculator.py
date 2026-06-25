from src.enums.status_effect import StatusEffect


def calc_catch_probability(
    catch_rate: int,
    ball_modifier: float,
    current_hp: int,
    max_hp: int,
    status: StatusEffect,
) -> float:
    """Pure catch chance in [0, 1]. All inputs are plain data — no RNG, no
    mutation, no BattlePokemon reference. Mirrors combat_calculator's shape."""
    hp_modifier = 1 - (current_hp / max_hp) * 0.5

    status_modifier = 1.0
    if status in (StatusEffect.SLEEP, StatusEffect.FREEZE):
        status_modifier = 2.0
    elif status in (StatusEffect.PARALYSIS, StatusEffect.BURN, StatusEffect.POISON):
        status_modifier = 1.5

    return min((catch_rate * ball_modifier * hp_modifier * status_modifier) / 255, 1.0)
