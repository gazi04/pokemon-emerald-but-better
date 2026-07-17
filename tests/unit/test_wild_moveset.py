from src.systems.wild_moveset import select_wild_moves, MAX_MOVES
from src.model.static.pokemon import (
    LearnsetMove,
    PokemonSpecies,
    PokemonStat,
    SpritePaths,
)


class FakeMove:
    def __init__(self, pp):
        self.pp = pp


class FakeDataLoader:
    """Minimal stand-in: maps move name -> pp, like DataLoader.get_move."""

    def __init__(self, pp_by_move):
        self._pp = pp_by_move

    def get_move(self, name):
        pp = self._pp.get(name)
        return FakeMove(pp) if pp is not None else None


def make_species(learnset):
    return PokemonSpecies(
        baseExp=62,
        catch_rate=45,
        abilities=["overgrow"],
        types=["grass"],
        evolution=None,
        sprites=SpritePaths(back="b.png", front="f.png"),
        stats=PokemonStat(
            hp=40,
            attack=65,
            defence=35,
            special_attack=45,
            special_defence=55,
            speed=70,
        ),
        learnset=learnset,
    )


def test_level_gates_out_higher_moves():
    species = make_species(
        [
            LearnsetMove("tackle", 1),
            LearnsetMove("growl", 1),
            LearnsetMove("spore", 9),
        ]
    )
    loader = FakeDataLoader({"tackle": 35, "growl": 40, "spore": 15})

    names = [m.name for m in select_wild_moves(species, 5, loader)]

    assert names == ["tackle", "growl"]  # spore@9 excluded at level 5


def test_includes_move_at_exact_level():
    species = make_species([LearnsetMove("tackle", 1), LearnsetMove("spore", 9)])
    loader = FakeDataLoader({"tackle": 35, "spore": 15})

    names = [m.name for m in select_wild_moves(species, 9, loader)]

    assert names == ["tackle", "spore"]


def test_caps_at_four_keeping_last_learned():
    species = make_species(
        [
            LearnsetMove("tackle", 1),
            LearnsetMove("growl", 2),
            LearnsetMove("toxic", 3),
            LearnsetMove("spore", 4),
            LearnsetMove("close combat", 5),
        ]
    )
    loader = FakeDataLoader(
        {
            "tackle": 35,
            "growl": 40,
            "toxic": 10,
            "spore": 15,
            "close combat": 5,
        }
    )

    names = [m.name for m in select_wild_moves(species, 50, loader)]

    assert len(names) == MAX_MOVES
    assert names == ["growl", "toxic", "spore", "close combat"]  # tackle@1 dropped


def test_resolves_pp_from_move_data():
    species = make_species([LearnsetMove("spore", 1)])
    loader = FakeDataLoader({"spore": 15})

    moves = select_wild_moves(species, 5, loader)

    assert moves[0].name == "spore"
    assert moves[0].pp == 15


def test_empty_learnset_falls_back_to_tackle():
    species = make_species([])
    loader = FakeDataLoader({})

    moves = select_wild_moves(species, 5, loader)

    assert [(m.name, m.pp) for m in moves] == [("tackle", 35)]


def test_unknown_move_is_skipped():
    species = make_species([LearnsetMove("tackle", 1), LearnsetMove("ghost_move", 1)])
    loader = FakeDataLoader({"tackle": 35})  # ghost_move absent

    names = [m.name for m in select_wild_moves(species, 5, loader)]

    assert names == ["tackle"]
