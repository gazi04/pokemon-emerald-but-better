"""The weather ↔ pokemon bridge.

WeatherState (src/model/battle/weather_state.py) owns the battle-wide weather
and deliberately never touches a BattlePokemon — it takes primitives. The
ability side of weather lives on the pokemon (ability_effects). These are the
three places the two meet, extracted from BattleSystem so that seam is one
named module instead of three methods scattered through the turn engine.
"""

from src.enums.effect_type import EffectType
from src.enums.stat import Stat
from src.enums.weather import Weather
from src.model.battle.battle_pokemon import BattlePokemon
from src.model.battle.weather_state import WeatherState
from src.model.static.pokemon import PokemonMove


def speed(pokemon: BattlePokemon, weather: WeatherState) -> int:
    """Speed for turn order, including Swift Swim / Chlorophyll in weather."""
    base = pokemon.get_stat(Stat.SPEED)
    return round(base * pokemon.weather_speed_multiplier(weather.kind))


def apply_move_weather(weather: WeatherState, move_data: PokemonMove) -> list[str]:
    """Summon weather from a move's `weather` effect, if it has one."""
    messages: list[str] = []
    for effect in move_data.effects:
        if effect.type == EffectType.WEATHER and effect.weather:
            messages.extend(weather.set(Weather(effect.weather)))
    return messages


def apply_end_of_turn(weather: WeatherState, *pokemons: BattlePokemon) -> list[str]:
    """Weather's per-turn effects on both active Pokémon, then its countdown.

    Heal abilities (Rain Dish/Ice Body) first, then sandstorm/hail chip on
    anything not immune. HP changes are published by post_turn's net-change
    check, so this only mutates and messages.
    """
    if not weather.is_active:
        return []

    messages: list[str] = []
    for pokemon in pokemons:
        if pokemon.current_hp <= 0:
            continue

        messages.extend(pokemon.weather_heal(weather.kind))

        takes_chip = weather.damages(pokemon.types) and not pokemon.absorbs_weather(
            weather.kind
        )
        if takes_chip:
            pokemon.take_damage(weather.residual_damage(pokemon.max_hp))
            messages.append(weather.residual_message(pokemon.name))

    messages.extend(weather.tick())
    return [m for m in messages if m]
