"""Tests for level-up move learning on BattlePokemon (learnset detection,
auto-learn into a free slot, and replacing a move when the set is full)."""
from src.model.battle.battle_pokemon import BattlePokemon, MAX_MOVES
from src.model.static.pokemon import (
    PokemonSpecies,
    SpritePaths,
    PokemonStat,
    LearnsetMove,
)
from src.model.save.player import PlayerPokemon, PlayerPokemonMove


LEARNSET = [
    LearnsetMove("tackle", 1),
    LearnsetMove("ember", 7),
    LearnsetMove("bite", 10),
]


def _mon(moves, learnset=LEARNSET, level=4):
    sp = PokemonSpecies(
        baseExp=62, catch_rate=45, abilities=[], types=["normal"], evolution=None,
        sprites=SpritePaths(back="b", front="f"),
        stats=PokemonStat(hp=50, attack=60, defence=50, special_attack=50,
                          special_defence=50, speed=45),
        learnset=learnset,
    )
    pp = PlayerPokemon(
        "mon", 999, level, 0, "x",
        [PlayerPokemonMove(n, 10) for n in moves], None,
    )
    return BattlePokemon.from_player(None, sp, pp, False), pp


def test_moves_learned_between_levels():
    mon, _ = _mon(["tackle"], level=4)
    # Crossing 4 -> 11 reaches ember(7) and bite(10).
    assert mon._moves_learned_between(4, 11) == ["ember", "bite"]


def test_already_known_moves_excluded():
    mon, _ = _mon(["tackle", "ember"], level=6)
    assert mon._moves_learned_between(6, 8) == []  # ember already known


def test_auto_learn_into_free_slot_persists_to_party():
    mon, party = _mon(["tackle"])
    assert mon.has_free_move_slot()
    mon.learn_move("ember", 25)
    # battle moves list is shared with the party member -> persists
    assert [m.name for m in party.moves] == ["tackle", "ember"]


def test_replace_move_when_full():
    mon, party = _mon(["a", "b", "c", "d"])
    assert not mon.has_free_move_slot()
    forgotten = mon.replace_move(2, "ember", 25)
    assert forgotten == "c"
    assert party.moves[2].name == "ember"
    assert len(party.moves) == MAX_MOVES
