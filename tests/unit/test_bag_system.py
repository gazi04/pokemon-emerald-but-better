"""Tests for the current BagSystem: heal / cure-status / restore-PP items,
including PP move-targeting and item eligibility."""
from unittest.mock import MagicMock


from src.systems.bag_system import BagSystem
from src.model.static.item import ItemSpecies
from src.model.static.pokemon import (
    PokemonMove,
    PokemonSpecies,
    SpritePaths,
    PokemonStat,
)
from src.model.save.player import PlayerSave, PlayerPokemon, PlayerPokemonMove, ItemStack
from src.enums.item_category import ItemCategory


# --- builders --------------------------------------------------------------


def _item(**kw) -> ItemSpecies:
    raw = {
        "description": "",
        "price": 0,
        "category": "medicine",
        "holdable": False,
        "battle_condition": None,
        "battle_attributes": None,
        "effects": [],
    }
    raw.update({k: v for k, v in kw.items() if k != "name"})
    species = ItemSpecies(raw)
    species.name = kw.get("name", "Item")
    return species


ITEMS = {
    "potion": _item(name="Potion", effects=[{"type": "heal", "amount": 20}]),
    "antidote": _item(
        name="Antidote", effects=[{"type": "cure_status", "status": "poison"}]
    ),
    "full heal": _item(
        name="Full Heal", effects=[{"type": "cure_status", "status": "all"}]
    ),
    "ether": _item(name="Ether", effects=[{"type": "restore_pp", "amount": 10}]),
}


def _species(base_hp=50):
    return PokemonSpecies(
        baseExp=62,
        catch_rate=45,
        abilities=[],
        types=["water"],
        evolution=None,
        sprites=SpritePaths(back="b", front="f"),
        stats=PokemonStat(
            hp=base_hp,
            attack=50,
            defence=50,
            special_attack=50,
            special_defence=50,
            speed=50,
        ),
        learnset=[],
    )


def _move(pp_max=35):
    return PokemonMove(
        name="tackle",
        category="physical",
        type="normal",
        power=40,
        accuracy=100,
        pp=pp_max,
        priority=0,
        crit=0,
        multi_hit=None,
        condition=None,
        effects=[],
    )


def make_bag(hp=30, level=50, status=None, moves=None):
    pokemon = PlayerPokemon(
        name="mudkip",
        hp=hp,
        level=level,
        exp=0,
        ability="torrent",
        moves=moves or [PlayerPokemonMove("tackle", 5)],
        held_item=None,
        status_condition=status,
    )
    save = PlayerSave(
        pokemon=[pokemon],
        items={
            name: ItemStack(name, 3, ItemCategory.MEDICINE) for name in ITEMS
        },
    )
    pm = MagicMock()
    pm.player = save
    pm.update_pokemon_hp.side_effect = save.update_hp
    pm.update_pokemon_status.side_effect = save.update_status
    pm.update_move_pp.side_effect = save.update_move_pp
    pm.consume_item.side_effect = save.consume_item

    dl = MagicMock()
    dl.get_item.side_effect = lambda n: ITEMS[n]
    dl.get_pokemon.return_value = _species()
    dl.get_move.return_value = _move()  # max pp 35

    return BagSystem(pm, dl), save, pokemon


# --- heal ------------------------------------------------------------------


def test_heal_restores_hp_and_consumes_item():
    bag, save, mon = make_bag(hp=30)
    assert bag.use_item("potion", "mudkip") is True
    assert mon.hp == 50
    assert save.items["potion"].count == 2


def test_heal_caps_at_max_hp():
    max_hp = PokemonStat.max_hp(50, 50)
    bag, save, mon = make_bag(hp=max_hp - 5, level=50)
    bag.use_item("potion", "mudkip")
    assert mon.hp == max_hp  # +20 clamped to max


def test_heal_rejected_at_full_hp_not_consumed():
    max_hp = PokemonStat.max_hp(50, 50)
    bag, save, mon = make_bag(hp=max_hp, level=50)
    assert bag.use_item("potion", "mudkip") is False
    assert save.items["potion"].count == 3  # untouched


# --- cure status -----------------------------------------------------------


def test_antidote_cures_matching_status():
    bag, save, mon = make_bag(status="poison")
    assert bag.use_item("antidote", "mudkip") is True
    assert mon.status_condition is None


def test_antidote_noop_on_wrong_status():
    bag, save, mon = make_bag(status="burn")
    assert bag.use_item("antidote", "mudkip") is False
    assert mon.status_condition == "burn"
    assert save.items["antidote"].count == 3


def test_full_heal_cures_any_status():
    bag, save, mon = make_bag(status="paralyzed")
    assert bag.use_item("full heal", "mudkip") is True
    assert mon.status_condition is None


# --- restore PP (move targeting) ------------------------------------------


def test_is_pp_item():
    bag, _, _ = make_bag()
    assert bag.is_pp_item("ether") is True
    assert bag.is_pp_item("potion") is False


def test_ether_restores_only_the_chosen_move():
    moves = [PlayerPokemonMove("tackle", 5), PlayerPokemonMove("growl", 2)]
    bag, save, mon = make_bag(moves=moves)
    assert bag.use_item("ether", "mudkip", move_index=1) is True
    assert mon.moves[0].pp == 5          # untouched
    assert mon.moves[1].pp == 2 + 10     # restored


def test_ether_noop_on_full_move_not_consumed():
    moves = [PlayerPokemonMove("tackle", 35)]  # already full (max 35)
    bag, save, mon = make_bag(moves=moves)
    assert bag.use_item("ether", "mudkip", move_index=0) is False
    assert save.items["ether"].count == 3


def test_ether_without_move_index_restores_all():
    moves = [PlayerPokemonMove("tackle", 5), PlayerPokemonMove("growl", 2)]
    bag, save, mon = make_bag(moves=moves)
    assert bag.use_item("ether", "mudkip") is True
    assert mon.moves[0].pp == 15
    assert mon.moves[1].pp == 12
