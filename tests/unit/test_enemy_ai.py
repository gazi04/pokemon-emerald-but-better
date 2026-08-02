from unittest.mock import MagicMock

from src.enums.effect_type import EffectType
from src.enums.stat import Stat
from src.enums.status_effect import StatusEffect
from src.model.battle.battle_pokemon import BattlePokemon
from src.model.save.player import PlayerPokemon, PlayerPokemonMove
from src.model.static.pokemon import (
    PokemonMove,
    PokemonMoveEffect,
    PokemonSpecies,
    PokemonStat,
    SpritePaths,
)
from src.systems.enemy_ai import EnemyAI


def make_profile(speed=50, types=None):
    stats = PokemonStat(
        hp=50, attack=60, defence=50, special_attack=50, special_defence=50, speed=speed
    )
    return PokemonSpecies(
        baseExp=62,
        catch_rate=45,
        abilities=[],
        types=types or ["normal"],
        evolution=None,
        sprites=SpritePaths(back="b.png", front="f.png"),
        stats=stats,
        learnset=[],
    )


def make_battle_pokemon(name="bulbasaur", speed=50, moves=None, is_enemy=False):
    profile = make_profile(speed=speed)
    pp = PlayerPokemon(
        name=name,
        hp=999,
        level=10,
        exp=0,
        ability="",
        moves=moves or [PlayerPokemonMove(name="tackle", pp=35)],
        held_item=None,
    )
    battle = BattlePokemon.from_player(None, profile, pp, is_enemy)
    battle.current_hp = battle.max_hp
    return battle


def make_poke_move(name="tackle", power: int | None = 40, accuracy=100, priority=0):
    return PokemonMove(
        name=name,
        category="physical",
        type="normal",
        power=power,
        accuracy=accuracy,
        pp=35,
        priority=priority,
        crit=0,
        multi_hit=None,
        condition=None,
        effects=[],
    )


def make_data_loader():
    dl = MagicMock()
    dl.require_move.side_effect = lambda name: make_poke_move(name=name)
    dl.types = {}  # empty type chart -> multiplier defaults to 1.0
    return dl


def test_copy_for_simulation_isolates_modifiers():
    original = make_battle_pokemon()
    clone = original.copy_for_simulation()

    clone.modifiers[Stat.ATTACK] = 3
    clone.current_hp -= 10

    assert original.modifiers[Stat.ATTACK] == 0
    assert original.current_hp == original.max_hp


def test_copy_for_simulation_shares_static_data_by_reference():
    original = make_battle_pokemon()
    clone = original.copy_for_simulation()

    # Immutable/never-mutated-during-simulation data should be shared, not
    # deep-copied — this is the whole point of the optimization.
    assert clone.moves is original.moves
    assert clone.stats is original.stats
    assert clone.source is original.source


def test_select_move_returns_valid_index_and_does_not_mutate_real_state():
    moves = [
        PlayerPokemonMove(name="tackle", pp=35),
        PlayerPokemonMove(name="scratch", pp=35),
    ]
    enemy = make_battle_pokemon("poochyena", moves=moves, is_enemy=True)
    player = make_battle_pokemon("mudkip")

    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    index = ai.select_move(enemy, player)

    assert index in (0, 1)
    # The real battle Pokemon must come out of AI lookahead untouched.
    assert enemy.current_hp == enemy.max_hp
    assert player.current_hp == player.max_hp
    assert enemy.modifiers[Stat.ATTACK] == 0
    assert player.modifiers[Stat.ATTACK] == 0


def test_select_move_returns_none_for_empty_moveset():
    enemy = make_battle_pokemon("poochyena", is_enemy=True)
    enemy.moves = []
    player = make_battle_pokemon("mudkip")

    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    assert ai.select_move(enemy, player) is None


# --- simulate_damage ---------------------------------------------------------


def test_simulate_damage_zero_for_status_move():
    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    attacker = make_battle_pokemon("poochyena", is_enemy=True)
    defender = make_battle_pokemon("mudkip")
    status_move = make_poke_move(power=None)

    assert ai.simulate_damage(attacker, defender, status_move) == 0


def test_simulate_damage_zero_when_defender_immune():
    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    attacker = make_battle_pokemon("poochyena", is_enemy=True)
    defender = make_battle_pokemon("mudkip")
    defender.immunity_to = lambda move: "It doesn't affect Mudkip…"

    assert ai.simulate_damage(attacker, defender, make_poke_move()) == 0


# --- simulate_effects_move ---------------------------------------------------


def test_simulate_effects_move_zero_when_no_effects():
    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    user = make_battle_pokemon("poochyena", is_enemy=True)
    target = make_battle_pokemon("mudkip")

    assert ai.simulate_effects_move(make_poke_move(), user, target) == 0


def test_simulate_effects_move_zero_when_target_immune():
    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    user = make_battle_pokemon("poochyena", is_enemy=True)
    target = make_battle_pokemon("mudkip")
    target.immunity_to = lambda move: "immune"
    move = make_poke_move()
    move.effects = [
        PokemonMoveEffect(
            target="opponent", type=EffectType.STAT, stat=Stat.ATTACK, change=-1
        )
    ]

    assert ai.simulate_effects_move(move, user, target) == 0


def test_simulate_effects_move_self_stat_boost_applies_and_scores_positive():
    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    user = make_battle_pokemon("poochyena", is_enemy=True)
    target = make_battle_pokemon("mudkip")
    move = make_poke_move()
    move.effects = [
        PokemonMoveEffect(
            target="self", type=EffectType.STAT, stat=Stat.ATTACK, change=2
        )
    ]

    score = ai.simulate_effects_move(move, user, target)

    assert score > 0
    assert user.modifiers[Stat.ATTACK] == 2


def test_simulate_effects_move_self_stat_boost_skipped_when_already_maxed():
    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    user = make_battle_pokemon("poochyena", is_enemy=True)
    user.modifiers[Stat.ATTACK] = 6
    target = make_battle_pokemon("mudkip")
    move = make_poke_move()
    move.effects = [
        PokemonMoveEffect(
            target="self", type=EffectType.STAT, stat=Stat.ATTACK, change=2
        )
    ]

    score = ai.simulate_effects_move(move, user, target)

    assert score == 0
    assert user.modifiers[Stat.ATTACK] == 6  # unchanged, still capped


def test_simulate_effects_move_opponent_stat_drop_scores_negative_for_user():
    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    user = make_battle_pokemon("poochyena", is_enemy=True)
    target = make_battle_pokemon("mudkip")
    move = make_poke_move()
    move.effects = [
        PokemonMoveEffect(
            target="opponent", type=EffectType.STAT, stat=Stat.DEFENCE, change=-1
        )
    ]

    score = ai.simulate_effects_move(move, user, target)

    assert score > 0  # lowering the opponent's stat is good for the AI
    assert target.modifiers[Stat.DEFENCE] == -1


def test_simulate_effects_move_stat_effect_missing_fields_skipped():
    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    user = make_battle_pokemon("poochyena", is_enemy=True)
    target = make_battle_pokemon("mudkip")
    move = make_poke_move()
    move.effects = [
        PokemonMoveEffect(target="self", type=EffectType.STAT, stat=None, change=None)
    ]

    assert ai.simulate_effects_move(move, user, target) == 0


def test_simulate_effects_move_applies_status_condition():
    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    user = make_battle_pokemon("poochyena", is_enemy=True)
    target = make_battle_pokemon("mudkip", speed=50)
    move = make_poke_move()
    move.effects = [
        PokemonMoveEffect(
            target="opponent",
            type=EffectType.STATUS_CONDITION,
            condition=StatusEffect.PARALYSIS,
            chance=100,
        )
    ]

    score = ai.simulate_effects_move(move, user, target)

    assert score == 35  # status_weights["paralyzed"]
    assert target.status_effect == StatusEffect.PARALYSIS


def test_simulate_effects_move_status_blocked_by_type_immunity():
    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    user = make_battle_pokemon("poochyena", is_enemy=True)
    target = make_battle_pokemon("torchic")
    target.types = ["fire"]
    move = make_poke_move()
    move.effects = [
        PokemonMoveEffect(
            target="opponent",
            type=EffectType.STATUS_CONDITION,
            condition=StatusEffect.BURN,
            chance=100,
        )
    ]

    score = ai.simulate_effects_move(move, user, target)

    assert score == 0
    assert target.status_effect == StatusEffect.NONE


def test_simulate_effects_move_status_noop_when_target_already_statused():
    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    user = make_battle_pokemon("poochyena", is_enemy=True)
    target = make_battle_pokemon("mudkip")
    target.status_effect = StatusEffect.POISON
    move = make_poke_move()
    move.effects = [
        PokemonMoveEffect(
            target="opponent",
            type=EffectType.STATUS_CONDITION,
            condition=StatusEffect.PARALYSIS,
            chance=100,
        )
    ]

    score = ai.simulate_effects_move(move, user, target)

    assert score == 0
    assert target.status_effect == StatusEffect.POISON  # untouched


def test_simulate_effects_move_status_condition_missing_skipped():
    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    user = make_battle_pokemon("poochyena", is_enemy=True)
    target = make_battle_pokemon("mudkip")
    move = make_poke_move()
    move.effects = [
        PokemonMoveEffect(
            target="opponent",
            type=EffectType.STATUS_CONDITION,
            condition=None,
            chance=100,
        )
    ]

    assert ai.simulate_effects_move(move, user, target) == 0


# --- _evaluate_ai_move edge cases --------------------------------------------


def test_evaluate_ai_move_zero_pp_is_worst_possible():
    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    enemy = make_battle_pokemon("poochyena", is_enemy=True)
    player = make_battle_pokemon("mudkip")
    zero_pp_move = PlayerPokemonMove(name="tackle", pp=0)

    assert ai._evaluate_ai_move(enemy, player, zero_pp_move, depth=2) == -float("inf")


def test_evaluate_ai_move_falls_back_to_hp_eval_when_player_has_no_pp():
    ai = EnemyAI(smartness=1.0, data_loader=make_data_loader())
    enemy = make_battle_pokemon("poochyena", is_enemy=True)
    player = make_battle_pokemon(
        "mudkip", moves=[PlayerPokemonMove(name="tackle", pp=0)]
    )
    ai_move = PlayerPokemonMove(name="tackle", pp=35)

    assert ai._evaluate_ai_move(enemy, player, ai_move, depth=2) == ai.evaluate_hp(
        enemy, player
    )


def test_select_move_falls_back_to_random_when_smartness_zero(monkeypatch):
    moves = [
        PlayerPokemonMove(name="tackle", pp=35),
        PlayerPokemonMove(name="scratch", pp=35),
    ]
    enemy = make_battle_pokemon("poochyena", moves=moves, is_enemy=True)
    player = make_battle_pokemon("mudkip")

    monkeypatch.setattr("random.choice", lambda seq: 1)
    ai = EnemyAI(smartness=0.0, data_loader=make_data_loader())

    assert ai.select_move(enemy, player) == 1
