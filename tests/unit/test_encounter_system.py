from unittest.mock import MagicMock, patch

from src.core.event_bus import global_bus
from src.core.events import BattleEncounterTriggeredEvent, PlayerFinishedMoveEvent
from src.model.motion.player_motion import PlayerMotion
from src.systems.encounter_system import EncounterSystem

FAKE_ENC = {
    "littleroot_town": {"grass": [{"name": "poochyena", "levels": [2, 4], "weight": 1}]}
}


def make_system(bush_tiles=None, map_name="littleroot_town", encounters=None):
    player_state = PlayerMotion(map_name=map_name)
    dl = MagicMock()
    dl.require_pokemon.return_value = MagicMock()
    # Cached table on the DataLoader. NOTE: this stub cannot catch a mismatch
    # between these keys and real map ids — that is what
    # tests/unit/test_encounter_data.py asserts against the real data files.
    dl.encounters = FAKE_ENC if encounters is None else encounters
    tiles = bush_tiles or {(5, 5)}
    system = EncounterSystem(tiles, player_state, dl)
    return system, player_state, dl


def fire_move_event(gx, gy, map_name="littleroot_town"):
    return PlayerFinishedMoveEvent(grid_x=gx, grid_y=gy, map_name=map_name)


# --- encounter triggered ---


def test_encounter_triggered_on_bush_tile():
    system, _player_state, _dl = make_system(bush_tiles={(5, 5)})
    received = []
    global_bus.subscribe(BattleEncounterTriggeredEvent, received.append)

    with patch("src.systems.encounter_system.random.random", return_value=0.0):
        system._on_player_moved(fire_move_event(5, 5))

    assert len(received) == 1
    assert received[0].pokemon_name == "poochyena"


def test_no_encounter_off_bush_tile():
    system, _, _ = make_system(bush_tiles={(5, 5)})
    received = []
    global_bus.subscribe(BattleEncounterTriggeredEvent, received.append)

    with patch("src.systems.encounter_system.random.random", return_value=0.0):
        system._on_player_moved(fire_move_event(3, 3))  # not in bush_tiles

    assert received == []


def test_no_encounter_when_random_exceeds_rate():
    system, _, _ = make_system(bush_tiles={(5, 5)})
    received = []
    global_bus.subscribe(BattleEncounterTriggeredEvent, received.append)

    # FAKE_ENC has no encounter_rate → falls back to ENCOUNTER_RATE (0.15);
    # random.random() == 1.0 is >= rate → no encounter
    with patch("src.systems.encounter_system.random.random", return_value=1.0):
        system._on_player_moved(fire_move_event(5, 5))

    assert received == []


# --- cleanup / resubscribe ---


def test_cleanup_stops_encounters():
    system, _, _ = make_system(bush_tiles={(5, 5)})
    system.cleanup()
    assert not system._subscribed

    received = []
    global_bus.subscribe(BattleEncounterTriggeredEvent, received.append)

    with patch("src.systems.encounter_system.random.random", return_value=0.0):
        system._on_player_moved(fire_move_event(5, 5))

    # _on_player_moved called directly — event is still published
    # but the system is no longer subscribed to PlayerFinishedMoveEvent on the bus
    assert not system._subscribed


def test_resubscribe_sets_subscribed_flag():
    system, _, _ = make_system()
    system.cleanup()
    assert not system._subscribed
    system.resubscribe()
    assert system._subscribed


def test_resubscribe_does_not_double_subscribe():
    system, _, _ = make_system()
    assert system._subscribed
    system.resubscribe()  # already subscribed, should no-op
    assert system._subscribed


# --- event payload ---


def test_encounter_event_has_pokemon_data():
    system, _, dl = make_system(bush_tiles={(2, 2)})
    fake_profile = MagicMock()
    dl.require_pokemon.return_value = fake_profile
    received = []
    global_bus.subscribe(BattleEncounterTriggeredEvent, received.append)

    with patch("src.systems.encounter_system.random.random", return_value=0.0):
        system._on_player_moved(fire_move_event(2, 2))

    assert received[0].pokemon_data is fake_profile


def test_no_encounter_on_map_without_data():
    # A genuinely unknown map is guarded here: no crash, no encounter. This is
    # correct for a map that has no table by design — it is NOT cover for a real
    # map whose id fails to match its key (the Route 101 bug), which this stubbed
    # test cannot see and test_encounter_data.py exists to catch.
    system, _, _ = make_system(bush_tiles={(5, 5)}, map_name="unknown_map")
    received = []
    global_bus.subscribe(BattleEncounterTriggeredEvent, received.append)

    with patch("src.systems.encounter_system.random.random", return_value=0.0):
        system._on_player_moved(fire_move_event(5, 5, map_name="unknown_map"))

    assert received == []


def test_no_encounter_when_table_has_no_grass_key():
    """A water/fishing-only table must not raise KeyError."""
    system, _, _ = make_system(
        bush_tiles={(5, 5)},
        encounters={
            "littleroot_town": {"encounter_rate": 1.0, "surf": [{"name": "x"}]}
        },
    )
    received = []
    global_bus.subscribe(BattleEncounterTriggeredEvent, received.append)

    with patch("src.systems.encounter_system.random.random", return_value=0.0):
        system._on_player_moved(fire_move_event(5, 5))

    assert received == []


def test_no_encounter_when_grass_list_is_empty():
    """An empty grass list passes the table truthiness guard, then would raise
    IndexError inside random.choices."""
    system, _, _ = make_system(
        bush_tiles={(5, 5)},
        encounters={"littleroot_town": {"encounter_rate": 1.0, "grass": []}},
    )
    received = []
    global_bus.subscribe(BattleEncounterTriggeredEvent, received.append)

    with patch("src.systems.encounter_system.random.random", return_value=0.0):
        system._on_player_moved(fire_move_event(5, 5))

    assert received == []


def test_encounter_level_within_declared_range():
    system, _, _ = make_system(bush_tiles={(5, 5)})
    received = []
    global_bus.subscribe(BattleEncounterTriggeredEvent, received.append)

    with patch("src.systems.encounter_system.random.random", return_value=0.0):
        system._on_player_moved(fire_move_event(5, 5))

    assert 2 <= received[0].pokemon_level <= 4
