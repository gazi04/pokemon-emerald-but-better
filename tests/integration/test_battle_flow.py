"""
Integration test: BattleSystem + real DataLoader (real data/) + SaveManager (tmp_path).
Runs a full battle to KO and verifies state consistency.
"""
import pytest

from src.core.event_bus import global_bus
from src.core.events import HpChangedEvent, PokemonFaintedEvent
from src.entities.pokemon_battle import PokemonBattle
from src.model.player import PlayerPokemon, PlayerPokemonMove
from src.systems.battle_system import BattleSystem


def _make_battle_pokemon(name, data_loader, level=10, is_enemy=False, move_name="tackle"):
    profile = data_loader.get_pokemon(name)
    pp = PlayerPokemon(name=name, hp=999, level=level, exp=0,
                       moves=[PlayerPokemonMove(name=move_name, pp=35)])
    battle = PokemonBattle(data=profile, isEnemy=is_enemy, playerPokemon=pp)
    battle.currentHp = battle.maxHp
    return battle


@pytest.fixture
def real_data_loader():
    """DataLoader pointing at the real data/ directory (run from project root)."""
    from src.core.data_loader import DataLoader
    return DataLoader()


def test_full_battle_to_ko_fires_fainted_event(real_data_loader, player_manager):
    your = _make_battle_pokemon("mudkip", real_data_loader, level=20)
    enemy = _make_battle_pokemon("poochyena", real_data_loader, level=1, is_enemy=True)
    # Level 1 poochyena has very low HP — should faint in one hit

    fainted = []
    global_bus.subscribe(PokemonFaintedEvent, fainted.append)

    bs = BattleSystem(your, enemy, player_manager, real_data_loader)

    # Execute up to 20 turns; call executeNextAction once more to flush postTurn
    for _ in range(20):
        bs.turn(0)
        while bs.turnQueue:
            bs.executeNextAction()
        bs.executeNextAction()  # empty queue → triggers postTurn → pokemonDeath
        if bs.battleState in ("end", "trainer switch"):
            break

    assert enemy.currentHp == 0 or your.currentHp == 0
    assert len(fainted) > 0


def test_hp_changed_events_fire_during_battle(real_data_loader, player_manager):
    your = _make_battle_pokemon("mudkip", real_data_loader, level=10)
    enemy = _make_battle_pokemon("treecko", real_data_loader, level=10, is_enemy=True)

    hp_events = []
    global_bus.subscribe(HpChangedEvent, hp_events.append)

    bs = BattleSystem(your, enemy, player_manager, real_data_loader)
    bs.turn(0)
    while bs.turnQueue:
        bs.executeNextAction()

    assert len(hp_events) > 0


def test_save_manager_hp_updated_after_battle(real_data_loader, player_manager):
    your = _make_battle_pokemon("mudkip", real_data_loader, level=5)
    enemy = _make_battle_pokemon("poochyena", real_data_loader, level=10, is_enemy=True)

    bs = BattleSystem(your, enemy, player_manager, real_data_loader)
    for _ in range(5):
        if your.currentHp <= 0 or enemy.currentHp <= 0:
            break
        bs.turn(0)
        while bs.turnQueue:
            bs.executeNextAction()

    bs.save()
    saved_hp = player_manager.player.get_pokemon("mudkip").hp
    assert saved_hp == your.currentHp
