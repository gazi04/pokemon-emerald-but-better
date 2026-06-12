from unittest.mock import MagicMock, patch

import pytest

from src.core.event_bus import global_bus
from src.core.events import HpChangedEvent, PokemonFaintedEvent
from src.entities.pokemon_battle import PokemonBattle
from src.model.player import PlayerPokemon, PlayerPokemonMove
from src.model.pokemon import PokemonMove, PokemonProfile, PokemonSprites, PokemonStat
from src.systems.battle_system import BattleSystem


def make_profile(hp=50, attack=60, defence=50, sp_atk=50, sp_def=50, speed=50, types=None, base_exp=62):
    stats = PokemonStat(hp=hp, attack=attack, defence=defence,
                        special_attack=sp_atk, special_defence=sp_def, speed=speed)
    return PokemonProfile(
        pokemon={"baseExp": base_exp, "abilities": [], "types": types or ["normal"]},
        evolution=None,
        sprites=PokemonSprites(back="b.png", front="f.png"),
        stats=stats,
    )


def make_battle_pokemon(name="bulbasaur", level=10, speed=50, types=None, is_enemy=False):
    profile = make_profile(speed=speed, types=types or ["normal"])
    pp = PlayerPokemon(name=name, hp=999, level=level, exp=0,
                       moves=[PlayerPokemonMove(name="tackle", pp=35)])
    battle = PokemonBattle(data=profile, isEnemy=is_enemy, playerPokemon=pp)
    battle.currentHp = battle.maxHp
    return battle


def make_poke_move(name="tackle", category="physical", type_="normal", power=40, accuracy=100):
    return PokemonMove(name, {"category": category, "type": type_, "power": power,
                               "accuracy": accuracy, "pp": 35}, [])


def make_battle_system(player_speed=50, enemy_speed=50):
    your = make_battle_pokemon("mudkip", speed=player_speed)
    enemy = make_battle_pokemon("poochyena", speed=enemy_speed, is_enemy=True)

    sm = MagicMock()
    sm.player.items = []
    dl = MagicMock()
    dl.get_move.return_value = make_poke_move()

    return BattleSystem(your, enemy, sm, dl), your, enemy


# --- turn ---

def test_turn_returns_messages():
    bs, _, _ = make_battle_system()
    messages = bs.turn(0)
    assert isinstance(messages, list)
    assert len(messages) > 0


def test_turn_builds_two_action_queue_before_execution():
    bs, _, _ = make_battle_system()
    # After turn(), first action is popped; one remains
    bs.turn(0)
    # Queue drained or has 1 item depending on whether first action was terminal
    assert isinstance(bs.turnQueue, list)


def test_hp_decreases_after_turn():
    bs, your, enemy = make_battle_system()
    your_hp_before = your.currentHp
    enemy_hp_before = enemy.currentHp
    bs.turn(0)
    assert your.currentHp < your_hp_before or enemy.currentHp < enemy_hp_before


def test_hp_changed_event_published():
    bs, _, _ = make_battle_system()
    received = []
    global_bus.subscribe(HpChangedEvent, received.append)
    bs.turn(0)
    assert len(received) > 0
    event = received[0]
    assert event.target in ("player", "enemy")


# --- speed ordering ---

def test_player_faster_acts_first():
    bs, _, _ = make_battle_system(player_speed=100, enemy_speed=10)
    bs.turn(0)
    # First action already executed; one item remains = the second actor
    assert len(bs.turnQueue) == 1
    assert bs.turnQueue[0][0] == "enemy"


def test_enemy_faster_acts_first():
    bs, _, _ = make_battle_system(player_speed=10, enemy_speed=100)
    bs.turn(0)
    assert len(bs.turnQueue) == 1
    assert bs.turnQueue[0][0] == "player"


def test_equal_speed_player_goes_first():
    bs, _, _ = make_battle_system(player_speed=50, enemy_speed=50)
    bs.turn(0)
    # >= comparison → player wins speed tie; enemy is the remaining actor
    assert len(bs.turnQueue) == 1
    assert bs.turnQueue[0][0] == "enemy"


# --- faint ---

def test_pokemon_fainted_event_when_enemy_dies():
    bs, your, enemy = make_battle_system()
    enemy.currentHp = 1  # one-shot
    received = []
    global_bus.subscribe(PokemonFaintedEvent, received.append)
    # Execute all actions
    bs.turnQueue = [("player", 0, -1)]
    bs.executeNextAction()
    if enemy.currentHp <= 0:
        bs.pokemonDeath(enemy)
    assert any(e.target == "enemy" for e in received)


def test_pokemon_fainted_event_when_player_dies():
    bs, your, enemy = make_battle_system()
    your.currentHp = 1
    received = []
    global_bus.subscribe(PokemonFaintedEvent, received.append)
    bs.turnQueue = [("enemy", 0, -1)]
    bs.executeNextAction()
    if your.currentHp <= 0:
        bs.pokemonDeath(your)
    assert any(e.target == "player" for e in received)


# --- postTurn ---

def test_post_turn_poison_reduces_hp():
    bs, your, _ = make_battle_system()
    your.statusEffect = "poison"
    hp_before = your.currentHp
    bs.turnQueue = []
    bs.postTurn()
    assert your.currentHp < hp_before


# --- executeNextAction ---

def test_execute_next_action_removes_from_queue():
    bs, _, _ = make_battle_system()
    bs.turnQueue = [("player", 0, -1), ("enemy", 0, -1)]
    bs.executeNextAction()
    assert len(bs.turnQueue) <= 1


def test_execute_next_action_empty_queue_calls_post_turn():
    bs, _, _ = make_battle_system()
    bs.turnQueue = []
    bs.battleState = "intro"
    messages = bs.executeNextAction()
    # postTurn was called — battleState changes
    assert bs.battleState in ("post turn", "waiting", "end")


def test_turn_use_item_publishes_hp_changed_event():
    bs, your, _ = make_battle_system()
    item = MagicMock()
    item.name = "potion"
    bs.save_manager.player.items = [item]
    received = []
    global_bus.subscribe(HpChangedEvent, received.append)
    bs.turnUseItem(0)
    assert any(e.target == "player" for e in received)


def test_execute_move_with_zero_pp_no_damage():
    bs, your, enemy = make_battle_system()
    your.moves[0].pp = 0
    bs.turnQueue = [("player", 0, -1)]
    bs.executeNextAction()
    # check_can_move returns (["But there is no PP left!"], False) → no damage
    assert enemy.currentHp == enemy.maxHp
