"""Pure weather rules: summoning, damage scaling, residual chip, and duration."""

from src.enums.weather import Weather
from src.model.battle.weather_state import WeatherState


# --- summoning --------------------------------------------------------------


def test_starts_clear():
    weather = WeatherState()
    assert not weather.is_active
    assert weather.kind == Weather.NONE


def test_set_activates_and_announces():
    weather = WeatherState()
    messages = weather.set(Weather.RAIN)

    assert weather.is_active
    assert weather.kind == Weather.RAIN
    assert weather.turns_left == 5
    assert messages == ["It started to rain!"]


def test_resummoning_same_weather_fails():
    weather = WeatherState()
    weather.set(Weather.SUN)
    assert weather.set(Weather.SUN) == ["But it failed!"]


def test_different_weather_overrides():
    weather = WeatherState()
    weather.set(Weather.RAIN)
    weather.set(Weather.SUN)
    assert weather.kind == Weather.SUN
    assert weather.turns_left == 5


# --- damage multipliers -----------------------------------------------------


def test_rain_boosts_water_and_damps_fire():
    weather = WeatherState(Weather.RAIN, 5)
    assert weather.damage_multiplier("water") == 1.5
    assert weather.damage_multiplier("fire") == 0.5
    assert weather.damage_multiplier("grass") == 1.0


def test_sun_boosts_fire_and_damps_water():
    weather = WeatherState(Weather.SUN, 5)
    assert weather.damage_multiplier("fire") == 1.5
    assert weather.damage_multiplier("water") == 0.5


def test_clear_and_chip_weather_do_not_scale_damage():
    assert WeatherState().damage_multiplier("water") == 1.0
    assert WeatherState(Weather.SANDSTORM, 5).damage_multiplier("fire") == 1.0


# --- residual chip ----------------------------------------------------------


def test_sandstorm_damages_most_types():
    weather = WeatherState(Weather.SANDSTORM, 5)
    assert weather.damages(["normal"])
    assert weather.damages(["water", "flying"])


def test_sandstorm_spares_rock_ground_steel():
    weather = WeatherState(Weather.SANDSTORM, 5)
    assert not weather.damages(["rock"])
    assert not weather.damages(["ground", "dragon"])
    assert not weather.damages(["steel"])


def test_hail_damages_all_but_ice():
    weather = WeatherState(Weather.HAIL, 5)
    assert weather.damages(["fire"])
    assert not weather.damages(["ice"])


def test_rain_and_sun_never_chip():
    assert not WeatherState(Weather.RAIN, 5).damages(["normal"])
    assert not WeatherState(Weather.SUN, 5).damages(["normal"])


def test_residual_damage_is_a_sixteenth():
    weather = WeatherState(Weather.SANDSTORM, 5)
    assert weather.residual_damage(160) == 10
    assert weather.residual_damage(8) == 1  # never rounds to zero


# --- duration ---------------------------------------------------------------


def test_tick_counts_down_and_reports_ongoing():
    weather = WeatherState(Weather.SANDSTORM, 3)
    assert weather.tick() == ["The sandstorm rages."]
    assert weather.turns_left == 2


def test_tick_clears_on_last_turn():
    weather = WeatherState(Weather.RAIN, 1)
    assert weather.tick() == ["The rain stopped."]
    assert not weather.is_active
    assert weather.kind == Weather.NONE


def test_tick_on_clear_weather_is_noop():
    assert WeatherState().tick() == []
