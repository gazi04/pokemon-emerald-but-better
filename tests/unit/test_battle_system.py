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
from src.model.static.trainer import Trainer
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
    bs, _your, enemy = make_battle_system()
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
    bs, your, _enemy = make_battle_system()
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
    bs, _your, _ = make_battle_system()
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


def test_add_caught_pokemon_full_party_still_succeeds():
    # PC boxes: a full party no longer blocks catching. The caught Pokémon is
    # handed to the save (which overflows it to a box), so the flow still
    # reports success with no extra message.
    bs, _, _ = make_battle_system()
    pm = cast(MagicMock, bs.player_manager)

    result = bs.add_caught_pokemon()

    pm.add_pokemon.assert_called_once()
    assert result["success"] is True
    assert result["messages"] == []


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


# --- empty enemy moveset (defensive bounds guard) ---


def test_select_move_returns_none_for_empty_moveset():
    from src.systems.enemy_ai import EnemyAI

    _, your, enemy = make_battle_system()
    enemy.moves = []
    ai = EnemyAI(1, MagicMock())
    assert ai.select_move(enemy, your) is None


def test_turn_does_not_raise_with_empty_enemy_moveset():
    bs, _, enemy = make_battle_system()
    enemy.moves = []
    messages = bs.turn(0)
    assert isinstance(messages, list)
    assert all(action[0] != "enemy" for action in bs.turn_queue)


def test_attempt_catch_does_not_raise_with_empty_enemy_moveset():
    bs, _, enemy = make_battle_system()
    enemy.moves = []
    enemy.current_hp = (
        enemy.max_hp
    )  # low catch chance -> exercises the break-free branch
    cast(
        MagicMock, bs.data_loader
    ).get_pokemon.return_value = None  # fall back to default catch_rate
    item_data = MagicMock()
    item_data.effects = []
    result = bs.attempt_catch(item_data)
    assert isinstance(result, dict)
    assert bs.turn_queue == [] or all(a[0] != "enemy" for a in bs.turn_queue)


# --- switch_turn / switch_pokemon ------------------------------------------


def test_switch_turn_builds_enemy_only_queue_and_executes():
    bs, _, _ = make_battle_system()
    messages = bs.switch_turn()
    assert isinstance(messages, list)
    # ai always has a move available -> queue was consumed by execute_next_action
    assert bs.turn_queue == []


def test_switch_turn_empty_queue_when_enemy_has_no_moves():
    bs, _, enemy = make_battle_system()
    enemy.moves = []
    messages = bs.switch_turn()
    assert isinstance(messages, list)
    assert bs.turn_queue == []


def _real_battle_system(player_manager, data_loader, enemy_name="poochyena"):
    your = make_battle_pokemon("mudkip")
    enemy = make_battle_pokemon(enemy_name, is_enemy=True)
    return BattleSystem(your, enemy, player_manager, data_loader), your, enemy


def test_switch_pokemon_swaps_active_and_returns_messages(player_manager, data_loader):
    player_manager.player.pokemon.insert(
        0,
        PlayerPokemon(
            name="torchic",
            hp=20,
            level=5,
            exp=0,
            ability="blaze",
            moves=[PlayerPokemonMove(name="ember", pp=25)],
            held_item=None,
        ),
    )
    bs, _, _ = _real_battle_system(player_manager, data_loader)

    messages = bs.switch_pokemon()

    assert any("torchic" in m for m in messages)
    assert bs.your_pokemon.name.lower() == "torchic"


def test_switch_pokemon_fainted_lead_returns_unable_message(
    player_manager, data_loader
):
    player_manager.player.pokemon.insert(
        0,
        PlayerPokemon(
            name="torchic",
            hp=0,
            level=5,
            exp=0,
            ability="blaze",
            moves=[PlayerPokemonMove(name="ember", pp=25)],
            held_item=None,
        ),
    )
    bs, _, _ = _real_battle_system(player_manager, data_loader)

    messages = bs.switch_pokemon()

    assert messages == ["torchic is unable to battle!"]


def test_switch_pokemon_raises_without_player_save():
    bs, _, _ = make_battle_system()
    cast(MagicMock, bs.player_manager).player = None
    try:
        bs.switch_pokemon()
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


# --- multi-hit moves ---------------------------------------------------------


def test_execute_move_multiple_times_reports_hit_count(monkeypatch):
    bs, your, enemy = make_battle_system()
    multi_move = make_poke_move(name="double kick")
    multi_move.multi_hit = [2, 2]
    cast(MagicMock, bs.data_loader).get_move.return_value = multi_move
    monkeypatch.setattr("src.systems.battle_system.random.randint", lambda a, b: 2)

    messages = bs._execute_move_multiple_times(your, enemy, 0, "enemy")

    assert any("Hit 2 time(s)!" in m for m in messages)


def test_execute_move_multiple_times_stops_when_defender_faints(monkeypatch):
    bs, your, enemy = make_battle_system()
    multi_move = make_poke_move(name="double kick", power=999)
    multi_move.multi_hit = [5, 5]
    cast(MagicMock, bs.data_loader).get_move.return_value = multi_move
    monkeypatch.setattr("src.systems.battle_system.random.randint", lambda a, b: 5)

    bs._execute_move_multiple_times(your, enemy, 0, "enemy")

    assert enemy.current_hp <= 0


# --- move conditions ----------------------------------------------------------


def test_check_move_condition_first_turn_only_fails_after_first_turn():
    bs, your, _ = make_battle_system()
    your.is_first_turn = False
    move = make_poke_move(name="fake out")
    move.condition = "first_turn_only"

    assert bs._check_move_condition(move, your) == "But fake out failed!"


def test_check_move_condition_not_consecutive_fails_on_repeat():
    bs, your, _ = make_battle_system()
    move = make_poke_move(name="outrage")
    move.condition = "not_consecutive"
    bs._last_player_move = "outrage"

    assert bs._check_move_condition(move, your) == "But outrage failed!"


def test_check_move_condition_returns_none_when_satisfied():
    bs, your, _ = make_battle_system()
    move = make_poke_move(name="tackle")
    move.condition = None

    assert bs._check_move_condition(move, your) is None


# --- protection / immunity short-circuits in _execute_move -------------------


def test_execute_move_defender_protected_short_circuits():
    bs, your, enemy = make_battle_system()
    enemy.is_protected = True

    messages = bs._execute_move(your, enemy, 0, "enemy", announce=False)

    assert messages == ["Poochyena protected itself!"]


def test_execute_move_defender_immune_short_circuits(monkeypatch):
    bs, your, enemy = make_battle_system()
    monkeypatch.setattr(enemy, "immunity_to", lambda move: "It doesn't affect enemy…")

    messages = bs._execute_move(your, enemy, 0, "enemy", announce=False)

    assert messages == ["It doesn't affect enemy…"]


# --- sync_active_to_save -------------------------------------------------------


def test_sync_active_to_save_calls_sync_to_source():
    bs, your, _ = make_battle_system()
    your.sync_to_source = MagicMock()

    bs.sync_active_to_save()

    your.sync_to_source.assert_called_once()


# --- post_turn death branches --------------------------------------------------


def test_post_turn_ends_immediately_on_player_death():
    bs, your, _ = make_battle_system()
    your.current_hp = 0
    bs.turn_queue = []

    messages = bs.post_turn()

    assert any("fainted" in m for m in messages)
    assert bs.battle_state == BattleState.PLAYER_FAINTED


def test_post_turn_ends_immediately_on_enemy_death():
    bs, _, enemy = make_battle_system()
    enemy.current_hp = 0
    bs.turn_queue = []

    messages = bs.post_turn()

    assert any("fainted" in m for m in messages)
    assert bs.battle_state == BattleState.END


# --- pokemon_death trainer switch ----------------------------------------------


def test_pokemon_death_trainer_switch_queues_next_pokemon():
    bs, _your, enemy = make_battle_system()
    enemy.current_hp = 0
    bs.is_trainer = True
    bs.trainer_party = list(
        Trainer(
            [
                {
                    "name": "zigzagoon",
                    "level": 8,
                    "ability": "pickup",
                    "held_item": None,
                    "moves": [{"name": "tackle", "pp": 35}],
                }
            ]
        ).party
    )

    bs.pokemon_death(enemy)

    assert bs.battle_state == BattleState.TRAINER_SWITCH
    assert bs.next_trainer_pokemon is not None
    assert bs.next_trainer_pokemon.name == "zigzagoon"
    assert bs.trainer_party == []


def test_pokemon_death_wild_enemy_ends_battle():
    bs, _, enemy = make_battle_system()
    enemy.current_hp = 0

    bs.pokemon_death(enemy)

    assert bs.battle_state == BattleState.END
    assert bs.next_trainer_pokemon is None


# --- has_usable_pokemon / complete_forced_switch -------------------------------


def test_has_usable_pokemon_true_when_team_has_hp(player_manager, data_loader):
    bs, _, _ = _real_battle_system(player_manager, data_loader)
    assert bs.has_usable_pokemon() is True


def test_has_usable_pokemon_false_when_team_fainted(player_manager, data_loader):
    player_manager.player.pokemon[0].hp = 0
    bs, _, _ = _real_battle_system(player_manager, data_loader)
    assert bs.has_usable_pokemon() is False


def test_has_usable_pokemon_raises_without_player_save():
    bs, _, _ = make_battle_system()
    cast(MagicMock, bs.player_manager).player = None
    try:
        bs.has_usable_pokemon()
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


def test_complete_forced_switch_brings_in_replacement(player_manager, data_loader):
    player_manager.player.pokemon.insert(
        0,
        PlayerPokemon(
            name="torchic",
            hp=20,
            level=5,
            exp=0,
            ability="blaze",
            moves=[PlayerPokemonMove(name="ember", pp=25)],
            held_item=None,
        ),
    )
    bs, _, _ = _real_battle_system(player_manager, data_loader)

    messages = bs.complete_forced_switch()

    assert any("Go torchic" in m for m in messages)
    assert bs.your_pokemon.name.lower() == "torchic"


def test_complete_forced_switch_raises_without_player_save():
    bs, _, _ = make_battle_system()
    cast(MagicMock, bs.player_manager).player = None
    try:
        bs.complete_forced_switch()
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


# --- move-learning flow ---------------------------------------------------------


def test_queue_and_pending_learn_helpers():
    bs, _, _ = make_battle_system()
    assert bs.has_pending_learn() is False
    assert bs.current_learning_move() is None

    bs.queue_moves_to_learn(["growl"])
    assert bs.has_pending_learn() is True


def test_next_move_to_learn_returns_none_when_queue_empty():
    bs, _, _ = make_battle_system()
    assert bs.next_move_to_learn() is None


def test_next_move_to_learn_skips_already_known_move():
    bs, your, _ = make_battle_system()
    your.knows_move = lambda name: name == "tackle"
    bs.queue_moves_to_learn(["tackle", "growl"])
    cast(MagicMock, bs.data_loader).get_move.return_value = make_poke_move(name="growl")

    result = bs.next_move_to_learn()

    assert result is not None
    assert result["type"] == "learned"
    assert bs._learn_queue == []


def test_next_move_to_learn_learns_when_free_slot():
    bs, your, _ = make_battle_system()
    your.knows_move = lambda name: False
    your.has_free_move_slot = lambda: True
    your.learn_move = MagicMock()
    bs.queue_moves_to_learn(["growl"])
    cast(MagicMock, bs.data_loader).get_move.return_value = make_poke_move(name="growl")

    result = bs.next_move_to_learn()

    assert result is not None
    assert result["type"] == "learned"
    your.learn_move.assert_called_once()


def test_next_move_to_learn_needs_replace_when_moveset_full():
    bs, your, _ = make_battle_system()
    your.knows_move = lambda name: False
    your.has_free_move_slot = lambda: False
    bs.queue_moves_to_learn(["growl"])
    cast(MagicMock, bs.data_loader).get_move.return_value = make_poke_move(name="growl")

    result = bs.next_move_to_learn()

    assert result is not None
    assert result["type"] == "needs_replace"
    assert bs._pending_learn == "growl"


def test_replace_learned_move_forgets_and_learns():
    bs, your, _ = make_battle_system()
    your.replace_move = MagicMock(return_value="tackle")
    bs._pending_learn = "growl"
    cast(MagicMock, bs.data_loader).get_move.return_value = make_poke_move(name="growl")

    messages = bs.replace_learned_move(0)

    your.replace_move.assert_called_once_with(0, "growl", 35)
    assert bs._pending_learn is None
    assert any("forgot Tackle" in m for m in messages)


def test_replace_learned_move_raises_without_pending():
    bs, _, _ = make_battle_system()
    try:
        bs.replace_learned_move(0)
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


def test_skip_learned_move_returns_decline_message():
    bs, your, _ = make_battle_system()
    bs._pending_learn = "growl"
    cast(MagicMock, bs.data_loader).get_move.return_value = make_poke_move(name="growl")

    messages = bs.skip_learned_move()

    assert messages == [f"{your.name} did not learn Growl."]
    assert bs._pending_learn is None


def test_skip_learned_move_raises_without_pending():
    bs, _, _ = make_battle_system()
    try:
        bs.skip_learned_move()
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


# --- attempt_catch --------------------------------------------------------------


def test_attempt_catch_uses_ball_modifier_from_catch_effect(monkeypatch, data_loader):
    bs, _, _enemy = make_battle_system()
    pokeball = data_loader.require_item("pokeball")
    captured_kwargs = {}

    def fake_calc(catch_rate, ball_modifier, current_hp, max_hp, status):
        captured_kwargs["ball_modifier"] = ball_modifier
        return 0.0

    monkeypatch.setattr("src.systems.battle_system.calc_catch_probability", fake_calc)
    monkeypatch.setattr("src.systems.battle_system.random.random", lambda: 0.99)
    monkeypatch.setattr("src.systems.battle_system.random.randint", lambda a, b: 0)

    bs.attempt_catch(pokeball)

    assert captured_kwargs["ball_modifier"] == 1


def test_attempt_catch_success_marks_caught(monkeypatch, data_loader):
    bs, _, _enemy = make_battle_system()
    pokeball = data_loader.require_item("pokeball")
    monkeypatch.setattr(
        "src.systems.battle_system.calc_catch_probability", lambda *a: 1.0
    )
    monkeypatch.setattr("src.systems.battle_system.random.random", lambda: 0.0)

    result = bs.attempt_catch(pokeball)

    assert result["success"] is True
    assert bs.battle_state == BattleState.CAUGHT


def test_attempt_catch_failure_with_moves_queues_enemy_turn(monkeypatch, data_loader):
    bs, _, _enemy = make_battle_system()
    pokeball = data_loader.require_item("pokeball")
    monkeypatch.setattr(
        "src.systems.battle_system.calc_catch_probability", lambda *a: 0.0
    )
    monkeypatch.setattr("src.systems.battle_system.random.random", lambda: 0.99)
    monkeypatch.setattr("src.systems.battle_system.random.randint", lambda a, b: 0)

    result = bs.attempt_catch(pokeball)

    assert result["success"] is False
    assert bs.turn_queue == [("enemy", 0, -1)]


def test_attempt_catch_failure_without_moves_leaves_empty_queue(
    monkeypatch, data_loader
):
    bs, _, enemy = make_battle_system()
    enemy.moves = []
    pokeball = data_loader.require_item("pokeball")
    monkeypatch.setattr(
        "src.systems.battle_system.calc_catch_probability", lambda *a: 0.0
    )
    monkeypatch.setattr("src.systems.battle_system.random.random", lambda: 0.99)

    result = bs.attempt_catch(pokeball)

    assert result["success"] is False
    assert bs.turn_queue == []


# --- item use: target and event correctness (R5) -----------------------------


def test_turn_use_item_publishes_real_before_and_after_hp():
    """R5: the item path used to publish old_hp == new_hp, unlike every other
    HP change in this file which captures hp_before before mutating."""
    bs, your, _ = make_battle_system()
    your.current_hp = your.max_hp - 10
    hp_before = your.current_hp
    # The save record is what a heal writes; the battle model must end up above it.
    your.source = PlayerPokemon(
        name="mudkip",
        hp=your.max_hp,
        level=your.level,
        exp=0,
        ability="",
        moves=[PlayerPokemonMove(name="tackle", pp=35)],
        held_item=None,
    )
    received = []
    global_bus.subscribe(HpChangedEvent, received.append)

    bs.turn_use_item("potion")

    player_events = [e for e in received if e.target == "player"]
    assert player_events, "no player HP event published"
    assert player_events[0].old_hp == hp_before
    assert player_events[0].new_hp != player_events[0].old_hp


def test_turn_use_item_on_benched_pokemon_names_that_pokemon():
    """Bundled fix B: healing a benched party member must not report the active
    mon's name."""
    bs, your, _ = make_battle_system()
    messages = bs.turn_use_item("potion", target_name="treecko")
    assert any("treecko" in m.lower() for m in messages)
    assert not any(your.name.lower() in m.lower() for m in messages)


def test_turn_use_item_on_benched_pokemon_publishes_no_player_bar_event():
    """Bundled fix B: the active mon's bar must not react to a benched heal."""
    bs, _your, _ = make_battle_system()
    received = []
    global_bus.subscribe(HpChangedEvent, received.append)

    bs.turn_use_item("potion", target_name="treecko")

    assert not [e for e in received if e.target == "player"]
