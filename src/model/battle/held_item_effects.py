"""Held-item hooks — free functions over a BattlePokemon.

Same shape and the same reason as ability_effects.py: BattleSystem fires these
during a turn, and they must work on an EnemyAI simulation clone, so nothing
here holds a reference to the pokemon it operates on.

Berries are consumed (removed from the holder *and* its save source); passive
items (choice/type/orb) stay equipped.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.enums.effect_type import EffectType
from src.enums.stat import Stat
from src.enums.status_effect import StatusEffect
from src.model.static.pokemon import PokemonMove

if TYPE_CHECKING:
    from src.model.battle.battle_pokemon import BattlePokemon


def consume(pokemon: BattlePokemon) -> None:
    pokemon.held_item = None
    if pokemon.source is not None:
        pokemon.source.held_item = None


def attack_multiplier(pokemon: BattlePokemon, move: PokemonMove) -> float:
    """Passive offensive item multiplier folded into damage: Life Orb / type
    boosters (damage_multiplier) and Choice Band/Specs (stat_multiplier)."""
    item = pokemon.held_item
    if not item or not item.battle_attributes:
        return 1.0
    attrs = item.battle_attributes
    multiplier = 1.0

    if attrs.damage_multiplier:
        move_type = item.battle_condition.move_type if item.battle_condition else None
        if move_type is None or move.type == move_type:
            multiplier *= attrs.damage_multiplier

    if attrs.stat_multiplier:
        stat = attrs.stat_multiplier.get("stat")
        mult = attrs.stat_multiplier.get("multiplier", 1.0)
        if (stat == "attack" and move.category == "physical") or (
            stat == "special_attack" and move.category == "special"
        ):
            multiplier *= mult

    return multiplier


def recoil_self(pokemon: BattlePokemon, move: PokemonMove) -> list[str]:
    """Life Orb: the attacker loses HP after landing a damaging move."""
    item = pokemon.held_item
    if not item or not move.power:
        return []
    for effect in item.effects:
        if effect.type == EffectType.RECOIL_TO_SELF and effect.percent:
            pokemon.take_damage(max(1, int(pokemon.max_hp * effect.percent / 100)))
            return [f"{pokemon.name} was hurt by its {item.name}!"]
    return []


def on_hit(
    pokemon: BattlePokemon, attacker: BattlePokemon, move: PokemonMove
) -> list[str]:
    """Rocky Helmet: the holder's item hurts the attacker on a contact hit."""
    item = pokemon.held_item
    if item is None:
        return []
    cond = item.battle_condition
    if not cond or cond.trigger != "on_hit":
        return []
    if cond.contact_only and move.category != "physical":
        return []
    for effect in item.effects:
        if effect.type == EffectType.RECOIL_TO_ATTACKER and effect.percent:
            attacker.take_damage(max(1, int(attacker.max_hp * effect.percent / 100)))
            return [f"{attacker.name} was hurt by {pokemon.name}'s {item.name}!"]
    return []


def turn_end(pokemon: BattlePokemon) -> list[str]:
    """Leftovers: restore a little HP at the end of the turn."""
    item = pokemon.held_item
    if item is None:
        return []
    cond = item.battle_condition
    if (
        not cond
        or cond.trigger != "on_turn_end"
        or pokemon.current_hp >= pokemon.max_hp
    ):
        return []
    for effect in item.effects:
        if effect.type == EffectType.HEAL and effect.percent:
            healed = max(1, int(pokemon.max_hp * effect.percent / 100))
            pokemon.current_hp = min(pokemon.max_hp, pokemon.current_hp + healed)
            return [f"{pokemon.name} restored a little HP using its {item.name}!"]
    return []


def consume_berry_on_hp(pokemon: BattlePokemon) -> list[str]:
    """Pinch berries (Sitrus/Oran heal, Salac/Liechi stat) — eaten when HP
    drops to/below the berry's threshold."""
    item = pokemon.held_item
    if item is None:
        return []
    cond = item.battle_condition
    if not cond or cond.trigger != "hp_threshold" or pokemon.current_hp <= 0:
        return []
    if pokemon.current_hp / pokemon.max_hp > (cond.threshold or 0):
        return []

    messages = [f"{pokemon.name} ate its {item.name}!"]
    for effect in item.effects:
        if effect.type == EffectType.HEAL:
            healed = (
                max(1, int(pokemon.max_hp * effect.percent / 100))
                if effect.percent
                else (effect.amount or 0)
            )
            pokemon.current_hp = min(pokemon.max_hp, pokemon.current_hp + healed)
            messages.append(f"{pokemon.name} restored its HP.")
        elif effect.type == EffectType.STAT and effect.stat:
            messages.extend(raise_stat(pokemon, Stat(effect.stat), effect.change or 1))
    consume(pokemon)
    return messages


def consume_berry_on_status(pokemon: BattlePokemon) -> list[str]:
    """Lum Berry: cure any status the moment one is inflicted."""
    item = pokemon.held_item
    if item is None:
        return []
    cond = item.battle_condition
    if not cond or cond.trigger != "on_status":
        return []
    if pokemon.status_effect == StatusEffect.NONE and pokemon.confusion_counter == 0:
        return []
    name = item.name
    pokemon.status_effect = StatusEffect.NONE
    pokemon.sleep_counter = 0
    pokemon.confusion_counter = 0
    consume(pokemon)
    return [f"{pokemon.name}'s {name} cured its status!"]


def raise_stat(pokemon: BattlePokemon, stat: Stat, change: int) -> list[str]:
    current = pokemon.modifiers.get(stat, 0)
    if current >= 6:
        return [f"{pokemon.name}'s {stat} won't go any higher!"]
    pokemon.modifiers[stat] = min(6, current + change)
    return [f"{pokemon.name}'s {stat} rose!"]
