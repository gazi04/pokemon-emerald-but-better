"""Ability hooks — free functions over a BattlePokemon.

Extracted from BattlePokemon rather than made a collaborator object it owns:
EnemyAI runs its lookahead on a `copy_for_simulation()` clone, which is a
shallow copy, so a handler holding a back-reference would still point at the
original pokemon. These functions take their subject as an argument instead.

Weather lives here too: the weather hooks are ability lookups
(`effects_for(pokemon, "weather")`), and WeatherState deliberately never
touches a BattlePokemon. Battle-wide weather is still owned by BattleSystem.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from src.enums.ability import AbilityCondition, AbilityTrigger, AbilityTypes
from src.enums.stat import Stat
from src.enums.status_effect import StatusEffect
from src.model.static.ability import AbilityEffect
from src.model.static.pokemon import PokemonMove

if TYPE_CHECKING:
    from src.model.battle.battle_pokemon import BattlePokemon


def display_name(pokemon: BattlePokemon) -> str:
    """The ability's name, for messages. Every caller is reached through
    `effects_for`, which yields nothing when there's no ability, so the
    empty fallback is unreachable in practice."""
    return pokemon.ability.name if pokemon.ability else ""


def effects_for(pokemon: BattlePokemon, trigger: str) -> list[AbilityEffect]:
    if not pokemon.ability or not pokemon.ability.effects:
        return []
    return [e for e in pokemon.ability.effects if e.trigger == trigger]


def condition_met(
    pokemon: BattlePokemon, effect: AbilityEffect, move: PokemonMove | None = None
) -> bool:
    """Gate an ability effect on its `condition` (None == always)."""
    condition = effect.condition
    if not condition:
        return True
    if condition == AbilityCondition.LOW_HP:
        return pokemon.current_hp <= pokemon.max_hp / 3
    if condition == AbilityCondition.CONTACT:
        return move is not None and move.category == "physical"
    if condition == AbilityCondition.GROUND_TYPE:
        return move is not None and move.type == "ground"
    if condition == AbilityCondition.HAS_STATUS_EFFECT:
        return pokemon.status_effect is not None

    return False


def attack_multiplier(
    pokemon: BattlePokemon, move: PokemonMove
) -> tuple[float, list[str]]:
    """Attacker hook (trigger 'on_attack'). Returns a damage multiplier and
    any UI messages — e.g. Blaze powering up the attack at low HP."""
    multiplier = 1.0
    messages: list[str] = []
    for effect in effects_for(pokemon, AbilityTrigger.ON_ATTACK):
        if effect.type != "damage_boost":
            continue
        if not condition_met(pokemon, effect, move):
            continue
        if move.type != effect.move_type:
            continue
        multiplier *= 1 + (effect.change or 0) / 100
        messages.append(
            f"{pokemon.name}'s {display_name(pokemon)} powered up the move!"
        )

    return multiplier, messages


def immunity_to(pokemon: BattlePokemon, move: PokemonMove) -> str | None:
    """Defender hook. Returns a message if this pokemon's ability makes it
    immune to `move` (e.g. Levitate vs Ground), else None."""
    for effect in effects_for(pokemon, AbilityTrigger.ON_HIT):
        if effect.type in [
            AbilityTypes.IMMUNITY,
            AbilityTypes.ABSORB,
        ] and condition_met(pokemon, effect, move):
            return f"It doesn't affect {pokemon.name}…"
    return None


def blocks_move_effect(pokemon: BattlePokemon) -> bool:
    return any(
        effect.type == AbilityTypes.IMMUNITY_MOVE_EFFECTS
        for effect in effects_for(pokemon, AbilityTrigger.ON_HIT)
    )


def has_status_immunity(pokemon: BattlePokemon, status: StatusEffect) -> bool:
    """
    Returns True if this pokemon's ability makes it immune to the status condition.
    e.g. Limber prevents paralysis, Immunity prevents poison.
    """
    return any(
        effect.type == AbilityTypes.IMMUNITY_STATUS_EFFECT and effect.status == status
        for effect in effects_for(pokemon, AbilityTrigger.ON_HIT)
    )


def blocks_stat_drop(pokemon: BattlePokemon, stat: Stat, change: int) -> bool:
    """
    Returns True if this pokemon's ability prevents a stat from being lowered.
    e.g. Clear Body / White Smoke block any move or
    ability that would reduce a stat stage.
    Only applies when change is negative (a drop); boosts are never blocked.
    """
    return change < 0 and any(
        effect.type == AbilityTypes.STAT_CHANGE and effect.stat == stat
        for effect in effects_for(pokemon, AbilityTrigger.ON_STAT_CHANGE)
    )


def on_hit(
    pokemon: BattlePokemon, attacker: BattlePokemon, move: PokemonMove
) -> list[str]:
    messages: list[str] = []
    for effect in effects_for(pokemon, AbilityTrigger.ON_HIT):
        if not condition_met(pokemon, effect, move):
            continue
        chance = effect.chance if effect.chance is not None else 1.0
        if random.random() >= chance:
            continue

        if effect.type == AbilityTypes.STATUS:
            victim = attacker if effect.target == "enemy" else pokemon
            applied, message = apply_status(pokemon, effect, victim)
            if applied:
                messages.append(message)

        elif effect.type == AbilityTypes.ABSORB:
            messages.extend(heal(pokemon, effect))

        elif (
            effect.type == AbilityTypes.PASSES_STATUS_EFFECT
            and pokemon.status_effect != StatusEffect.NONE
        ):
            attacker.apply_status_effect(pokemon.status_effect)
            pokemon.status_effect = StatusEffect.NONE

    return messages


def apply_status(
    pokemon: BattlePokemon, effect: AbilityEffect, destination: BattlePokemon
):
    status = status_from(effect.status)
    if status is None:
        return (False, "")

    if not destination.apply_status_effect(status):
        return (False, "")

    return (
        True,
        f"{destination.name} was {status.value} by "
        f"{pokemon.name}'s {display_name(pokemon)}!",
    )


def heal(pokemon: BattlePokemon, effect: AbilityEffect) -> list[str]:
    if effect.change is None:
        return []

    regained = int(pokemon.max_hp * effect.change / 100)
    pokemon.current_hp = min(pokemon.max_hp, pokemon.current_hp + regained)
    return [f"{pokemon.name} restored HP using {display_name(pokemon)}!"]


def weather_on_switch_in(pokemon: BattlePokemon) -> str | None:
    """The weather this pokemon's ability summons on entry (Drought → sun),
    or None. Returned as the raw string; BattleSystem maps it to Weather."""
    for effect in effects_for(pokemon, "on_switch_in"):
        if effect.type == "weather" and effect.weather:
            return effect.weather
    return None


def weather_speed_multiplier(pokemon: BattlePokemon, weather: str) -> float:
    """Swift Swim / Chlorophyll: a speed multiplier while their weather is up."""
    for effect in effects_for(pokemon, "weather"):
        if effect.type == "speed" and effect.weather == weather:
            return 1 + (effect.change or 0) / 100
    return 1.0


def weather_heal(pokemon: BattlePokemon, weather: str) -> list[str]:
    """Rain Dish / Ice Body: heal a little at end of turn in their weather."""
    for effect in effects_for(pokemon, "weather"):
        if (
            effect.type == "heal"
            and effect.weather == weather
            and pokemon.current_hp < pokemon.max_hp
        ):
            healed = max(1, int(pokemon.max_hp * (effect.change or 0) / 100))
            pokemon.current_hp = min(pokemon.max_hp, pokemon.current_hp + healed)
            return [f"{pokemon.name} restored HP with {display_name(pokemon)}!"]
    return []


def absorbs_weather(pokemon: BattlePokemon, weather: str) -> bool:
    """Whether this pokemon's ability makes it immune to `weather`'s chip —
    e.g. Ice Body thrives in hail, so it heals instead of taking damage."""
    return any(
        effect.type == "heal" and effect.weather == weather
        for effect in effects_for(pokemon, "weather")
    )


def on_switch_in(pokemon: BattlePokemon, opponent: BattlePokemon) -> list[str]:
    messages = []
    for effect in effects_for(pokemon, "on_switch_in"):
        if not condition_met(pokemon, effect):
            continue

        if effect.type == "stat_change":
            target = opponent if effect.target == "enemy" else pokemon
            messages.extend(pokemon._apply_stat_effect(effect, target))
            messages.append(f"{pokemon.name}'s {display_name(pokemon)} took effect!")

        elif effect.type == "status":
            target = opponent if effect.target == "enemy" else pokemon
            applied, message = apply_status(pokemon, effect, target)
            if applied:
                messages.append(message)

    return messages


def on_turn_end(pokemon: BattlePokemon, opponent: BattlePokemon) -> list[str]:
    messages = []
    for effect in effects_for(pokemon, "on_turn_end"):
        if not condition_met(pokemon, effect):
            continue

        if effect.type == "stat_change":
            target = opponent if effect.target == "enemy" else pokemon
            messages.extend(pokemon._apply_stat_effect(effect, target))

        elif effect.type == "cure_status":
            if pokemon.status_effect != StatusEffect.NONE:
                chance = effect.chance if effect.chance is not None else 1.0
                if random.random() < chance:
                    cured = pokemon.status_effect.value
                    pokemon.status_effect = StatusEffect.NONE
                    pokemon.sleep_counter = 0
                    messages.append(
                        f"{pokemon.name}'s {display_name(pokemon)} cured its {cured}!"
                    )

        elif effect.type == "heal":
            messages.extend(heal(pokemon, effect))

    return messages


def status_from(value) -> StatusEffect | None:
    if not value:
        return None
    try:
        return StatusEffect(value)
    except ValueError:
        return None
