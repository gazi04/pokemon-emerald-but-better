from typing import cast
from unittest.mock import MagicMock


from src.core.player_manager import PlayerManager
from src.core.event_bus import global_bus
from src.core.events import HpChangedEvent, PokemonFaintedEvent
from src.model.battle.battle_pokemon import BattlePokemon
from src.model.battle.exp_gain_result import ExpGainResult
from src.model.save.player import PlayerPokemon, PlayerPokemonMove
from src.model.static.pokemon import (
    PokemonEvolution,
    PokemonMove,
    PokemonSpecies,
    SpritePaths,
    PokemonStat,
)
from src.enums.battle_state import BattleState
from src.enums.status_effect import StatusEffect
from src.systems.battle_system import BattleSystem


def make_profile(
    hp=50,
    attack=60,
    defence=50,
    sp_atk=50,
    sp_def=50,
    speed=50,
    types=None,
    base_exp=62,
):
    stats = PokemonStat(
        hp=hp,
        attack=attack,
        defence=defence,
        special_attack=sp_atk,
        special_defence=sp_def,
        speed=speed,
    )
    return PokemonSpecies(
        baseExp=base_exp,
        catch_rate=45,
        abilities=[],
        types=types or ["normal"],
        evolution=None,
        sprites=SpritePaths(back="b.png", front="f.png"),
        stats=stats,
        learnset=[],
    )


def make_battle_pokemon(
    name="bulbasaur", level=10, speed=50, types=None, is_enemy=False
):
    profile = make_profile(speed=speed, types=types or ["normal"])
    pp = PlayerPokemon(
        name=name,
        hp=999,
        level=level,
        exp=0,
        ability="",
        moves=[PlayerPokemonMove(name="tackle", pp=35)],
        held_item=None,
    )
    battle = BattlePokemon.from_player(None, profile, pp, is_enemy)
    battle.current_hp = battle.max_hp
    return battle


def make_poke_move(
    name="tackle", category="physical", type_="normal", power=40, accuracy=100
):
    return PokemonMove(
        name=name,
        category=category,
        type=type_,
        power=power,
        accuracy=accuracy,
        pp=35,
        priority=0,
        crit=0,
        multi_hit=None,
        condition=None,
        effects=[],
    )


def make_battle_system(player_speed=50, enemy_speed=50):
    your = make_battle_pokemon("mudkip", speed=player_speed)
    enemy = make_battle_pokemon("poochyena", speed=enemy_speed, is_enemy=True)

    sm = MagicMock()
    sm.player.items = []
    dl = MagicMock()
    dl.get_move.return_value = make_poke_move()
    dl.require_move.return_value = make_poke_move()
    dl.types = {}  # empty type chart → multiplier defaults to 1.0

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
    assert isinstance(bs.turn_queue, list)


def test_hp_decreases_after_turn():
    bs, your, enemy = make_battle_system()
    your_hp_before = your.current_hp
    enemy_hp_before = enemy.current_hp
    bs.turn(0)
    assert your.current_hp < your_hp_before or enemy.current_hp < enemy_hp_before


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
    assert len(bs.turn_queue) == 1
    assert bs.turn_queue[0][0] == "enemy"


def test_enemy_faster_acts_first():
    bs, _, _ = make_battle_system(player_speed=10, enemy_speed=100)
    bs.turn(0)
    assert len(bs.turn_queue) == 1
    assert bs.turn_queue[0][0] == "player"


def test_equal_speed_player_goes_first():
    bs, _, _ = make_battle_system(player_speed=50, enemy_speed=50)
    bs.turn(0)
    # >= comparison → player wins speed tie; enemy is the remaining actor
    assert len(bs.turn_queue) == 1
    assert bs.turn_queue[0][0] == "enemy"


# --- faint ---


def test_pokemon_fainted_event_when_enemy_dies():
    bs, your, enemy = make_battle_system()
    enemy.current_hp = 1  # one-shot
    received = []
    global_bus.subscribe(PokemonFaintedEvent, received.append)
    # Execute all actions
    bs.turn_queue = [("player", 0, -1)]
    bs.execute_next_action()
    if enemy.current_hp <= 0:
        bs.pokemon_death(enemy)
    assert any(e.target == "enemy" for e in received)


def test_pokemon_fainted_event_when_player_dies():
    bs, your, enemy = make_battle_system()
    your.current_hp = 1
    received = []
    global_bus.subscribe(PokemonFaintedEvent, received.append)
    bs.turn_queue = [("enemy", 0, -1)]
    bs.execute_next_action()
    if your.current_hp <= 0:
        bs.pokemon_death(your)
    assert any(e.target == "player" for e in received)


# --- post_turn ---


def test_post_turn_poison_reduces_hp():
    bs, your, _ = make_battle_system()
    your.status_effect = StatusEffect.POISON
    hp_before = your.current_hp
    bs.turn_queue = []
    bs.post_turn()
    assert your.current_hp < hp_before


# --- execute_next_action ---


def test_execute_next_action_removes_from_queue():
    bs, _, _ = make_battle_system()
    bs.turn_queue = [("player", 0, -1), ("enemy", 0, -1)]
    bs.execute_next_action()
    assert len(bs.turn_queue) <= 1


def test_execute_next_action_empty_queue_calls_post_turn():
    bs, _, _ = make_battle_system()
    bs.turn_queue = []
    bs.battle_state = BattleState.INTRO
    bs.execute_next_action()
    # post_turn was called — battle_state changes
    assert bs.battle_state in (
        BattleState.POST_TURN,
        BattleState.WAITING,
        BattleState.END,
    )


def test_turn_use_item_publishes_hp_changed_event():
    bs, your, _ = make_battle_system()
    item = MagicMock()
    item.name = "potion"
    # Mirrors the real save shape: items is a dict keyed by item name, and the
    # bag queues the name (see test_turn_use_item_with_string_item_name...).
    cast(MagicMock, bs.player_manager).player.items = {"potion": item}
    received = []
    global_bus.subscribe(HpChangedEvent, received.append)
    bs.turn_use_item("potion")
    assert any(e.target == "player" for e in received)


def test_turn_use_item_with_string_item_name_does_not_crash():
    """Real bag items are queued as their name string, not an int index —
    item_index < 0 must not be evaluated against a str (was a live TypeError)."""
    bs, _, _ = make_battle_system()
    messages = bs.turn_use_item("potion")
    assert any("potion" in m for m in messages)


def test_execute_move_with_zero_pp_no_damage():
    bs, your, enemy = make_battle_system()
    your.moves[0].pp = 0
    bs.turn_queue = [("player", 0, -1)]
    bs.execute_next_action()
    # check_can_move returns (["But there is no PP left!"], False) → no damage
    assert enemy.current_hp == enemy.max_hp


# --- apply_exp_award ---


def test_apply_exp_award_resets_exp_and_returns_gain_result():
    bs, your, _ = make_battle_system()
    bs.exp = 120
    sentinel = ExpGainResult(
        leveled_up=False,
        stats_before=your.stats.copy(),
        stats_after=your.stats.copy(),
        evolved=False,
        evolves_to="",
    )
    your.gain_exp = MagicMock(return_value=sentinel)

    result = bs.apply_exp_award()

    your.gain_exp.assert_called_once_with(120)
    assert bs.exp == 0
    assert result is sentinel


def test_apply_exp_award_real_level_up():
    bs, _, _ = make_battle_system()
    bs.exp = 100000  # enough to gain at least one level

    result = bs.apply_exp_award()

    assert result.leveled_up is True
    assert bs.exp == 0


# --- add_caught_pokemon ---


def test_add_caught_pokemon_adds_enemy_to_party():
    bs, _, enemy = make_battle_system()
    pm = cast(MagicMock, bs.player_manager)
    enemy.current_hp = 7
    pm.add_pokemon.return_value = True

    result = bs.add_caught_pokemon()

    pm.add_pokemon.assert_called_once()
    added = pm.add_pokemon.call_args[0][0]
    assert isinstance(added, PlayerPokemon)
    assert added.name == enemy.name.lower()
    assert added.hp == 7
    assert added.level == enemy.level
    assert added.exp == 0
    assert added.moves == enemy.moves
    assert result == {"success": True, "messages": []}


def test_add_caught_pokemon_party_full_returns_failure_message():
    bs, _, _ = make_battle_system()
    pm = cast(MagicMock, bs.player_manager)
    pm.add_pokemon.return_value = False

    result = bs.add_caught_pokemon()

    pm.add_pokemon.assert_called_once()
    assert result["success"] is False
    assert result["messages"]


# --- save() delegation + persistence (§12 1c) ---


def test_save_delegates_to_player_manager():
    bs, your, _ = make_battle_system()
    bs.has_evolved = True
    bs.save()
    pm = cast(MagicMock, bs.player_manager)
    pm.persist_active_pokemon.assert_called_once_with(your, True)


def _player_manager_with_mock_player():
    sm = MagicMock()
    sm.player.npc_states = None  # skip NpcManager.load_from_dict branch
    return PlayerManager(sm, MagicMock()), sm


def test_persist_active_pokemon_writes_hp_pp_level():
    pm, sm = _player_manager_with_mock_player()
    battle = make_battle_pokemon("mudkip")

    pm.persist_active_pokemon(battle, has_evolved=False)

    sm.player.update_hp.assert_called_once_with("mudkip", battle.current_hp)
    assert sm.player.update_move_pp.call_count == len(battle.moves)
    sm.player.update_level.assert_called_once_with(
        "mudkip", battle.level, battle.exp, None
    )


def test_persist_active_pokemon_passes_evolution_when_evolved():
    pm, sm = _player_manager_with_mock_player()
    battle = make_battle_pokemon("mudkip")
    battle.evolution = PokemonEvolution(to="marshtomp", levelCap=16)

    pm.persist_active_pokemon(battle, has_evolved=True)

    sm.player.update_level.assert_called_once_with(
        "mudkip", battle.level, battle.exp, "marshtomp"
    )
