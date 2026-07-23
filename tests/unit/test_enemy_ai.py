from unittest.mock import MagicMock

from src.enums.stat import Stat
from src.model.battle.battle_pokemon import BattlePokemon
from src.model.save.player import PlayerPokemon, PlayerPokemonMove
from src.model.static.pokemon import (
    PokemonMove,
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


def make_poke_move(name="tackle", power=40, accuracy=100, priority=0):
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
