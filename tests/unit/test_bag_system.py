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
from src.model.save.player import (
    PlayerSave,
    PlayerPokemon,
    PlayerPokemonMove,
    ItemStack,
)
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
    "poke ball": _item(name="Poke Ball", category="pokeball"),
    "oran berry": _item(name="Oran Berry", category="berry", holdable=True),
    "potion (not holdable)": _item(name="Potion", category="medicine", holdable=False),
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
        boxs=[],
        items={name: ItemStack(name, 3, ItemCategory.MEDICINE) for name in ITEMS},
    )
    pm = MagicMock()
    pm.player = save
    pm.update_pokemon_hp.side_effect = save.update_hp
    pm.update_pokemon_status.side_effect = save.update_status
    pm.update_move_pp.side_effect = save.update_move_pp
    pm.consume_item.side_effect = save.consume_item

    dl = MagicMock()
    # BagSystem uses both: require_* where a miss is a bug, get_* where it probes.
    dl.get_item.side_effect = lambda n: ITEMS.get(n)
    dl.require_item.side_effect = lambda n: ITEMS[n]
    dl.require_pokemon.return_value = _species()
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
    bag, _save, mon = make_bag(hp=max_hp - 5, level=50)
    bag.use_item("potion", "mudkip")
    assert mon.hp == max_hp  # +20 clamped to max


def test_heal_rejected_at_full_hp_not_consumed():
    max_hp = PokemonStat.max_hp(50, 50)
    bag, save, _mon = make_bag(hp=max_hp, level=50)
    assert bag.use_item("potion", "mudkip") is False
    assert save.items["potion"].count == 3  # untouched


# --- cure status -----------------------------------------------------------


def test_antidote_cures_matching_status():
    bag, _save, mon = make_bag(status="poison")
    assert bag.use_item("antidote", "mudkip") is True
    assert mon.status_condition is None


def test_antidote_noop_on_wrong_status():
    bag, save, mon = make_bag(status="burn")
    assert bag.use_item("antidote", "mudkip") is False
    assert mon.status_condition == "burn"
    assert save.items["antidote"].count == 3


def test_full_heal_cures_any_status():
    bag, _save, mon = make_bag(status="paralyzed")
    assert bag.use_item("full heal", "mudkip") is True
    assert mon.status_condition is None


# --- restore PP (move targeting) ------------------------------------------


def test_is_pp_item():
    bag, _, _ = make_bag()
    assert bag.is_pp_item("ether") is True
    assert bag.is_pp_item("potion") is False


def test_ether_restores_only_the_chosen_move():
    moves = [PlayerPokemonMove("tackle", 5), PlayerPokemonMove("growl", 2)]
    bag, _save, mon = make_bag(moves=moves)
    assert bag.use_item("ether", "mudkip", move_index=1) is True
    assert mon.moves[0].pp == 5  # untouched
    assert mon.moves[1].pp == 2 + 10  # restored


def test_ether_noop_on_full_move_not_consumed():
    moves = [PlayerPokemonMove("tackle", 35)]  # already full (max 35)
    bag, save, _mon = make_bag(moves=moves)
    assert bag.use_item("ether", "mudkip", move_index=0) is False
    assert save.items["ether"].count == 3


def test_ether_without_move_index_restores_all():
    moves = [PlayerPokemonMove("tackle", 5), PlayerPokemonMove("growl", 2)]
    bag, _save, mon = make_bag(moves=moves)
    assert bag.use_item("ether", "mudkip") is True
    assert mon.moves[0].pp == 15
    assert mon.moves[1].pp == 12


# --- catch / held items ------------------------------------------------------
#
# These use their own bag builder (rather than `make_bag`'s all-medicine
# inventory) since pokeball/held-item stacks need real ItemCategory values on
# the ItemStack itself, and give_held_item/take_held_item mutate
# `pokemon.held_item` through PlayerManager rather than through PlayerSave.


def _bag_for(held_item=None, item_stacks=None):
    pokemon = PlayerPokemon(
        name="mudkip",
        hp=30,
        level=50,
        exp=0,
        ability="torrent",
        moves=[PlayerPokemonMove("tackle", 5)],
        held_item=held_item,
    )
    save = PlayerSave(pokemon=[pokemon], boxs=[], items=item_stacks or {})

    pm = MagicMock()
    pm.player = save
    pm.consume_item.side_effect = save.consume_item
    pm.add_item.side_effect = lambda item_id, count=1: save.add_item(
        item_id, ITEMS[item_id].category, count
    )
    pm.update_pokemon_held_item.side_effect = lambda _pid, item_id: setattr(
        pokemon, "held_item", item_id
    )

    dl = MagicMock()
    dl.get_item.side_effect = lambda n: ITEMS.get(n)

    return BagSystem(pm, dl), save, pokemon


def test_use_pokeball_succeeds_and_consumes_one():
    bag, save, _mon = _bag_for(
        item_stacks={"poke ball": ItemStack("poke ball", 5, ItemCategory.POKEBALL)}
    )
    result = bag.use_pokeball("poke ball")
    assert result is not None and result.name == "Poke Ball"
    assert save.items["poke ball"].count == 4


def test_use_pokeball_fails_when_count_zero():
    bag, save, _mon = _bag_for(
        item_stacks={"poke ball": ItemStack("poke ball", 0, ItemCategory.POKEBALL)}
    )
    assert bag.use_pokeball("poke ball") is None
    assert save.items["poke ball"].count == 0


def test_use_pokeball_fails_on_wrong_category():
    bag, save, _mon = _bag_for(
        item_stacks={"potion": ItemStack("potion", 3, ItemCategory.MEDICINE)}
    )
    assert bag.use_pokeball("potion") is None
    assert save.items["potion"].count == 3


def test_use_pokeball_fails_when_not_in_inventory():
    bag, _save, _mon = _bag_for()
    assert bag.use_pokeball("poke ball") is None


def test_give_held_item_succeeds_on_empty_handed_pokemon():
    bag, save, mon = _bag_for(
        item_stacks={"oran berry": ItemStack("oran berry", 2, ItemCategory.BERRY)}
    )
    assert bag.give_held_item("oran berry", "mudkip") is True
    assert mon.held_item == "oran berry"
    assert save.items["oran berry"].count == 1


def test_give_held_item_fails_when_already_holding():
    bag, save, mon = _bag_for(
        held_item="oran berry",
        item_stacks={"oran berry": ItemStack("oran berry", 2, ItemCategory.BERRY)},
    )
    assert bag.give_held_item("oran berry", "mudkip") is False
    assert mon.held_item == "oran berry"
    assert save.items["oran berry"].count == 2  # untouched


def test_give_held_item_fails_when_item_not_holdable():
    bag, _save, mon = _bag_for(
        item_stacks={
            "potion (not holdable)": ItemStack(
                "potion (not holdable)", 3, ItemCategory.MEDICINE
            )
        }
    )
    assert bag.give_held_item("potion (not holdable)", "mudkip") is False
    assert mon.held_item is None


def test_give_held_item_fails_for_unknown_pokemon():
    bag, _save, _mon = _bag_for(
        item_stacks={"oran berry": ItemStack("oran berry", 1, ItemCategory.BERRY)}
    )
    assert bag.give_held_item("oran berry", "torchic") is False


def test_take_held_item_returns_item_to_bag():
    bag, save, mon = _bag_for(held_item="oran berry")
    assert bag.take_held_item("mudkip") is True
    assert mon.held_item is None
    assert save.items["oran berry"].count == 1


def test_take_held_item_fails_when_nothing_held():
    bag, save, mon = _bag_for(held_item=None)
    assert bag.take_held_item("mudkip") is False
    assert mon.held_item is None
    assert save.items == {}


def test_get_items_filters_zero_count_and_groups_by_category():
    bag, _save, _mon = _bag_for(
        item_stacks={
            "poke ball": ItemStack("poke ball", 2, ItemCategory.POKEBALL),
            "oran berry": ItemStack("oran berry", 0, ItemCategory.BERRY),
            "potion": ItemStack("potion", 1, ItemCategory.MEDICINE),
        }
    )
    result = bag.get_items()
    assert ItemCategory.BERRY not in result  # zero-count stack filtered out
    assert [s.name for s in result[ItemCategory.POKEBALL]] == ["poke ball"]
    assert [s.name for s in result[ItemCategory.MEDICINE]] == ["potion"]


# --- live inventory ---------------------------------------------------------
# L9: BagSystem bound player_manager.player.items once in __init__, so after a
# save reload it read a detached dict.


def test_bag_reads_the_current_save_after_a_reload():
    bag, _, _ = make_bag()

    reloaded = PlayerSave(
        pokemon=[],
        boxs=[],
        items={"potion": ItemStack("potion", 7, ItemCategory.MEDICINE)},
    )
    bag.player_manager.player = reloaded

