"""
Integration test: BattleSystem + real DataLoader (real data/) + SaveManager (tmp_path).
Runs a full battle to KO and verifies state consistency.
"""

import pytest

from src.core.event_bus import global_bus
from src.core.events import HpChangedEvent
from src.model.battle.battle_pokemon import BattlePokemon
from src.model.save.player import PlayerPokemon, PlayerPokemonMove
from src.enums.battle_state import BattleState
from src.systems.battle_system import BattleSystem


def _make_battle_pokemon(
    name, data_loader, level=10, is_enemy=False, move_name="tackle"
):
    profile = data_loader.get_pokemon(name)
    pp = PlayerPokemon(
        name=name,
        hp=999,
        level=level,
        exp=0,
        ability="",
        moves=[PlayerPokemonMove(name=move_name, pp=35)],
        held_item=None,
    )
    battle = BattlePokemon.from_player(None, profile, pp, is_enemy)
    battle.current_hp = battle.max_hp
    return battle


@pytest.fixture
def real_data_loader():
    """DataLoader pointing at the real data/ directory (run from project root)."""
    from src.core.data_loader import DataLoader

    return DataLoader()


def test_full_battle_runs_to_a_knockout(real_data_loader, player_manager):
    """Observes the faint through battle state rather than PokemonFaintedEvent,
    which had no production consumer and was removed."""
    your = _make_battle_pokemon("mudkip", real_data_loader, level=20)
    enemy = _make_battle_pokemon("poochyena", real_data_loader, level=1, is_enemy=True)
    # Level 1 poochyena has very low HP — should faint in one hit

    bs = BattleSystem(your, enemy, player_manager, real_data_loader)

    # Execute up to 20 turns; call execute_next_action once more to flush post_turn
    for _ in range(20):
        bs.turn(0)
        while bs.turn_queue:
            bs.execute_next_action()
        bs.execute_next_action()  # empty queue → triggers post_turn → pokemon_death
        if bs.battle_state in (BattleState.END, BattleState.TRAINER_SWITCH):
            break

    assert enemy.current_hp == 0 or your.current_hp == 0
    assert bs.battle_state in (
        BattleState.END,
        BattleState.TRAINER_SWITCH,
        BattleState.PLAYER_FAINTED,
    )


def test_hp_changed_events_fire_during_battle(real_data_loader, player_manager):
    your = _make_battle_pokemon("mudkip", real_data_loader, level=10)
    enemy = _make_battle_pokemon("treecko", real_data_loader, level=10, is_enemy=True)

    hp_events = []
    global_bus.subscribe(HpChangedEvent, hp_events.append)

    bs = BattleSystem(your, enemy, player_manager, real_data_loader)
    bs.turn(0)
    while bs.turn_queue:
        bs.execute_next_action()

    assert len(hp_events) > 0


def test_save_manager_hp_updated_after_battle(real_data_loader, player_manager):
    your = _make_battle_pokemon("mudkip", real_data_loader, level=5)
    enemy = _make_battle_pokemon("poochyena", real_data_loader, level=10, is_enemy=True)

    bs = BattleSystem(your, enemy, player_manager, real_data_loader)
    for _ in range(5):
        if your.current_hp <= 0 or enemy.current_hp <= 0:
            break
        bs.turn(0)
        while bs.turn_queue:
            bs.execute_next_action()

    bs.save()
    saved_hp = player_manager.player.get_pokemon("mudkip").hp
    assert saved_hp == your.current_hp
