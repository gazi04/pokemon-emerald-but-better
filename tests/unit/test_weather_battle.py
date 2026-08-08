"""Weather wired into the battle: moves and abilities summon it, it scales
damage and turn order, and it chips/heals at end of turn."""

from unittest.mock import MagicMock

from src.enums.weather import Weather
from src.model.battle.battle_pokemon import BattlePokemon
from src.model.static.ability import Ability
from src.model.static.pokemon import (
    PokemonMove,
    PokemonMoveEffect,
    PokemonSpecies,
    SpritePaths,
    PokemonStat,
)
from src.model.save.player import PlayerPokemon, PlayerPokemonMove
from src.enums.effect_type import EffectType
from src.enums.stat import Stat
from src.systems.battle_system import BattleSystem


def _species(types=("normal",), speed=50):
    return PokemonSpecies(
        baseExp=62,
        catch_rate=45,
        abilities=[],
        types=list(types),
        evolution=None,
        sprites=SpritePaths(back="b", front="f"),
        stats=PokemonStat(100, 60, 50, 50, 50, speed),
        learnset=[],
    )


def _mon(ability=None, types=("normal",), speed=50, is_enemy=False, moves=None):
    ab = Ability(ability) if ability else None
    pp = PlayerPokemon(
        "mon", 999, 20, 0, "x", moves or [PlayerPokemonMove("tackle", 35)], None
    )
    b = BattlePokemon.from_player(ab, _species(types, speed), pp, is_enemy)
    b.current_hp = b.max_hp
    return b


def _system(your, enemy):
    sm = MagicMock()
    sm.player.items = []
    dl = MagicMock()
    dl.types = {}
    return BattleSystem(your, enemy, sm, dl)


def _weather_move(weather):
    return PokemonMove(
        "rain dance",
        "status",
        "water",
        None,
        None,
        5,
        0,
        0,
        None,
        None,
        [PokemonMoveEffect(target="self", type=EffectType.WEATHER, weather=weather)],
    )


def _drought():
    return {
        "name": "Drought",
        "description": "",
        "effects": [
            {
                "trigger": "on_switch_in",
                "type": "weather",
                "target": "self",
                "weather": "sun",
            }
        ],
    }


def _swift_swim():
    return {
        "name": "Swift Swim",
        "description": "",
        "effects": [
            {
                "trigger": "weather",
                "type": "speed",
                "target": "self",
                "weather": "rain",
                "change": 100,
            }
        ],
    }


def _ice_body():
    return {
        "name": "Ice Body",
        "description": "",
        "effects": [
            {
                "trigger": "weather",
                "type": "heal",
                "target": "self",
                "weather": "hail",
                "change": 6,
            }
        ],
    }


# --- moves summon weather ---------------------------------------------------


def test_move_summons_weather():
    system = _system(_mon(), _mon(is_enemy=True))
    messages = system._apply_move_weather(_weather_move("rain"))

    assert system.weather.kind == Weather.RAIN
    assert "It started to rain!" in messages


# --- abilities summon weather on entry --------------------------------------


def test_entry_ability_summons_weather():
    system = _system(_mon(_drought()), _mon(is_enemy=True))
    messages = system.start_battle()

    assert system.weather.kind == Weather.SUN
    assert any("kicked in" in m for m in messages)


def test_slower_weather_ability_wins():
    # Both set weather; the slower one activates last and overrides.
    fast = _mon(_drought(), speed=200)  # sun
    slow_rain = {
        "name": "Drizzle",
        "description": "",
        "effects": [
            {
                "trigger": "on_switch_in",
                "type": "weather",
                "target": "self",
                "weather": "rain",
            }
        ],
    }
    slow = _mon(slow_rain, speed=1, is_enemy=True)
    system = _system(slow, fast)
    system.start_battle()
    assert system.weather.kind == Weather.RAIN


# --- weather scales turn order ----------------------------------------------


def test_swift_swim_doubles_speed_in_rain():
    mon = _mon(_swift_swim(), speed=50)
    system = _system(mon, _mon(is_enemy=True))
    base_speed = mon.get_stat(Stat.SPEED)

    assert system._weather_speed(mon) == base_speed  # clear: no boost
    system.weather.set(Weather.RAIN)
    assert system._weather_speed(mon) == 2 * base_speed


def test_swift_swim_only_helps_in_its_weather():
    mon = _mon(_swift_swim(), speed=50)
    system = _system(mon, _mon(is_enemy=True))
    system.weather.set(Weather.SUN)  # wrong weather for Swift Swim
    assert system._weather_speed(mon) == mon.get_stat(Stat.SPEED)


# --- end-of-turn chip + immunity + heal -------------------------------------


def test_sandstorm_chips_non_immune_and_ticks():
    your = _mon(types=("normal",))
    enemy = _mon(types=("rock",), is_enemy=True)
    system = _system(your, enemy)
    system.weather.set(Weather.SANDSTORM, turns=3)

    system._apply_weather_end_of_turn()

    assert your.current_hp == your.max_hp - your.max_hp // 16  # chipped
    assert enemy.current_hp == enemy.max_hp  # rock is immune
    assert system.weather.turns_left == 2  # ticked


def test_ice_body_heals_and_ignores_hail_chip():
    # A Normal-type Ice Body holder: hail would normally chip it, but the
    # ability absorbs the weather and heals instead.
    your = _mon(_ice_body(), types=("normal",))
    your.current_hp = your.max_hp // 2
    system = _system(your, _mon(is_enemy=True))
    system.weather.set(Weather.HAIL)

    before = your.current_hp
    system._apply_weather_end_of_turn()
    assert your.current_hp > before  # net heal, no chip cancelling it out


def test_weather_expires_after_its_duration():
    system = _system(_mon(), _mon(is_enemy=True))
    system.weather.set(Weather.RAIN, turns=2)

    system._apply_weather_end_of_turn()
    assert system.weather.is_active
    system._apply_weather_end_of_turn()
    assert not system.weather.is_active
