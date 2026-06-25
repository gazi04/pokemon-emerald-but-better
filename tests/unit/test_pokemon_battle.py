from src.model.battle.battle_pokemon import BattlePokemon
from src.enums.stat import Stat
from src.enums.status_effect import StatusEffect
from src.model.save.player import PlayerPokemon, PlayerPokemonMove
from src.model.static.pokemon import (
    PokemonEvolution,
    PokemonMove,
    PokemonMoveEffect,
    PokemonSpecies,
    SpritePaths,
    PokemonStat,
)


def make_profile(
    hp=50,
    attack=60,
    defence=50,
    sp_atk=50,
    sp_def=50,
    speed=45,
    types=None,
    base_exp=62,
    evolution=None,
):
    stats = PokemonStat(
        hp=hp,
        attack=attack,
        defence=defence,
        special_attack=sp_atk,
        special_defence=sp_def,
        speed=speed,
    )
    sprites = SpritePaths(back="back.png", front="front.png")
    return PokemonSpecies(
        baseExp=base_exp,
        catch_rate=45,
        abilities=["overgrow"],
        types=types or ["grass"],
        evolution=evolution,
        sprites=sprites,
        stats=stats,
    )


def make_battle(
    name="bulbasaur",
    level=10,
    hp_override=None,
    types=None,
    base_exp=62,
    is_enemy=False,
    profile=None,
):
    profile = profile or make_profile(types=types or ["grass"], base_exp=base_exp)
    player_pokemon = PlayerPokemon(
        name=name,
        hp=999,
        level=level,
        exp=0,
        moves=[PlayerPokemonMove(name="tackle", pp=35)],
    )
    battle = BattlePokemon.from_player(profile, player_pokemon, is_enemy)
    battle.current_hp = battle.max_hp
    if hp_override is not None:
        battle.current_hp = hp_override
    return battle


def make_move(
    name="tackle",
    category="physical",
    type_="normal",
    power=40,
    accuracy=100,
    pp=35,
    effects=None,
):
    return PokemonMove(
        name=name,
        category=category,
        type=type_,
        power=power,
        accuracy=accuracy,
        pp=pp,
        effects=effects or [],
    )


# --- calculate_stats ---


def test_stats_scale_with_level():
    low = make_battle(level=5)
    high = make_battle(level=50)
    assert high.stats.attack > low.stats.attack
    assert high.stats.hp > low.stats.hp


def test_level_10_hp_formula():
    pb = make_battle(level=10)
    # hp = ((2 * 50 * 10) // 100) + 5 + 10 = 10 + 5 + 10 = 25
    expected = ((2 * 50 * 10) // 100) + 5 + 10
    assert pb.stats.hp == expected


# --- take_damage ---


def test_take_damage_reduces_hp():
    pb = make_battle()
    before = pb.current_hp
    pb.take_damage(10)
    assert pb.current_hp == before - 10


def test_take_damage_clamps_to_zero():
    pb = make_battle()
    pb.take_damage(9999)
    assert pb.current_hp == 0


def test_take_damage_does_not_go_negative():
    pb = make_battle()
    pb.take_damage(9999)
    assert pb.current_hp >= 0


# --- execute_effects: stat stages ---


def test_execute_effects_stat_boost_increases_modifier():
    attacker = make_battle()
    defender = make_battle(is_enemy=True)
    effect = PokemonMoveEffect(target="self", type="stat", stat="attack", change=1)
    move = make_move(effects=[effect])
    attacker.execute_effects(move, defender)
    assert attacker.modifiers[Stat.ATTACK] == 1


def test_execute_effects_stat_drop_on_opponent():
    attacker = make_battle()
    defender = make_battle(is_enemy=True)
    effect = PokemonMoveEffect(target="opponent", type="stat", stat="defence", change=-1)
    move = make_move(effects=[effect])
    attacker.execute_effects(move, defender)
    assert defender.modifiers[Stat.DEFENCE] == -1


def test_stat_stage_capped_at_plus_six():
    pb = make_battle()
    pb.modifiers[Stat.ATTACK] = 6
    effect = PokemonMoveEffect(target="self", type="stat", stat="attack", change=1)
    move = make_move(effects=[effect])
    messages = pb.execute_effects(move, make_battle())
    assert pb.modifiers[Stat.ATTACK] == 6
    assert any("won't go any higher" in m for m in messages)


def test_stat_stage_capped_at_minus_six():
    attacker = make_battle()
    defender = make_battle(is_enemy=True)
    defender.modifiers[Stat.ATTACK] = -6
    effect = PokemonMoveEffect(target="opponent", type="stat", stat="attack", change=-1)
    move = make_move(effects=[effect])
    messages = attacker.execute_effects(move, defender)
    assert defender.modifiers[Stat.ATTACK] == -6
    assert any("won't go any lower" in m for m in messages)


# --- execute_effects: status conditions ---


def test_execute_effects_applies_poison():
    attacker = make_battle()
    defender = make_battle(is_enemy=True)
    effect = PokemonMoveEffect(target="opponent", type="status condition", condition="poison", chance=100)
    move = make_move(effects=[effect])
    attacker.execute_effects(move, defender)
    assert defender.status_effect == StatusEffect.POISON


# --- after_a_turn ---


def test_after_a_turn_poison_reduces_hp():
    pb = make_battle()
    pb.status_effect = StatusEffect.POISON
    before = pb.current_hp
    messages = pb.after_a_turn()
    assert pb.current_hp < before
    assert any("poison" in m.lower() for m in messages)


def test_after_a_turn_no_status_no_damage():
    pb = make_battle()
    before = pb.current_hp
    pb.after_a_turn()
    assert pb.current_hp == before


# --- gain_exp ---


def test_gain_exp_below_threshold_no_level_up():
    pb = make_battle(level=5)
    initial_level = pb.level
    result = pb.gain_exp(1)  # level^3 = 125 needed; 1 exp is way below
    assert not result.leveled_up
    assert pb.level == initial_level


def test_gain_exp_enough_causes_level_up():
    pb = make_battle(level=5)
    # Level 5 needs 5^3 = 125 exp to level up
    result = pb.gain_exp(125)
    assert result.leveled_up
    assert pb.level == 6


def test_gain_exp_evolution_flag():
    evo = PokemonEvolution(to="ivysaur", levelCap=16)
    profile = make_profile(evolution=evo)
    pb = make_battle(level=15, profile=profile)
    # Give enough exp to reach level 16
    result = pb.gain_exp(pb.level**3)
    assert result.evolved
    assert result.evolves_to == "ivysaur"


def test_gain_exp_multiple_level_ups():
    pb = make_battle(level=5)
    # level 5 needs 125 (5³), level 6 needs 216 (6³) → 400 clears both
    result = pb.gain_exp(400)
    assert pb.level >= 7
    assert result.leveled_up


def test_status_overwrites_existing_currently():
    # Current behavior: no guard prevents overwriting an existing status.
    # This documents the known bug — in real Pokémon, a 2nd status can't apply.
    attacker = make_battle()
    defender = make_battle(is_enemy=True)
    defender.status_effect = StatusEffect.PARALYSIS
    effect = PokemonMoveEffect(target="opponent", type="status condition", condition="poison", chance=100)
    attacker.execute_effects(make_move(effects=[effect]), defender)
    assert defender.status_effect == StatusEffect.POISON


def test_sync_from_source_updates_current_hp():
    pb = make_battle()
    pb.source.hp = 5
    pb.sync_from_source()
    assert pb.current_hp == 5
