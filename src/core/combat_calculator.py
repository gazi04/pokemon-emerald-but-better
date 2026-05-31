import random

from src.util import calculateMultiplier
from src.model.combat_result import CombatResult
from src.model.pokemon import PokemonMove, PokemonStat


def calculate_damage(
    attacker_level: int,
    attacker_stats: PokemonStat,
    attacker_types: list[str],
    attacker_modifiers: dict,
    attacker_status: str,
    move_data: PokemonMove,
    defender_stats: PokemonStat,
    defender_types: list[str],
    defender_modifiers: dict,
    crit_modifier: int,
) -> CombatResult:
    """
    Pure damage calculation. All inputs are plain data — no PokemonBattle
    references. Returns a CombatResult; never mutates anything.
    """
    messages = []

    # --- Accuracy check ---
    if not _check_accuracy(move_data.accuracy, attacker_modifiers, defender_modifiers):
        return CombatResult(
            damage=0,
            effectiveness=1.0,
            is_critical=False,
            is_miss=True,
            messages=["It missed."],
        )

    # --- No damage moves ---
    if not move_data.power or move_data.category == "status":
        return CombatResult(
            damage=0, effectiveness=1.0, is_critical=False, is_miss=False
        )

    is_physical = move_data.category == "physical"

    # --- Stat selection ---
    a = _get_stat(
        "attack" if is_physical else "special attack",
        attacker_stats,
        attacker_modifiers,
        attacker_status,
    )
    d = _get_stat(
        "defence" if is_physical else "special defence",
        defender_stats,
        defender_modifiers,
        "",
    )

    # --- STAB ---
    stab = 1.5 if move_data.type in attacker_types else 1.0

    # --- Type effectiveness ---
    effectiveness = calculateMultiplier(move_data.type, defender_types)
    if effectiveness >= 2:
        messages.append("Its super effective.")
    elif 0 < effectiveness < 1:
        messages.append("Its not very effective.")
    elif effectiveness == 0:
        messages.append("No effect.")

    # --- Critical hit ---
    is_critical = _roll_critical(crit_modifier)
    if is_critical:
        # Crits ignore stat stage modifiers on defence
        d = defender_stats.defence if is_physical else defender_stats.special_defence
        messages.append("A critical hit!")

    crit_multiplier = 2 if is_critical else 1

    # --- Damage formula ---
    raw = (
        (((2 * attacker_level / 5 + 1) * move_data.power * a / d) / 50 + 2)
        * stab
        * effectiveness
        * crit_multiplier
    )

    return CombatResult(
        damage=round(raw),
        effectiveness=effectiveness,
        is_critical=is_critical,
        is_miss=False,
        messages=messages,
    )


# ---------------------------------------------------------------------------
# Private helpers — pure functions, no side effects
# ---------------------------------------------------------------------------


def _check_accuracy(
    accuracy, attacker_modifiers: dict, defender_modifiers: dict
) -> bool:
    if not accuracy:
        return True

    stage = attacker_modifiers.get("accuracy", 0) - defender_modifiers.get("evasion", 0)
    stage = max(-6, min(6, stage))

    if stage < 0:
        multiplier = 3 / (3 - abs(stage))
    elif stage > 0:
        multiplier = (3 + stage) / 3
    else:
        multiplier = 1

    return random.randint(1, 100) <= accuracy * multiplier


def _roll_critical(crit_modifier: int) -> bool:
    tier = min(crit_modifier, 4)
    probabilities = {0: 16, 1: 8, 2: 4, 3: 3, 4: 2}
    return random.randint(1, probabilities[tier]) == 1


def _get_stat(stat: str, stats: PokemonStat, modifiers: dict, status: str) -> float:
    """Apply stat stage modifier and status penalties, return effective stat value."""
    stage = modifiers.get(stat, 0)

    if stage > 0:
        fraction = (2 + stage) / 2
    elif stage < 0:
        fraction = 2 / (2 + abs(stage))
    else:
        fraction = 1.0

    raw = getattr(stats, stat.replace(" ", "_"), 0)

    if stat == "speed" and status == "paralyzed":
        return round(raw * fraction * 0.5)

    return round(raw * fraction)
