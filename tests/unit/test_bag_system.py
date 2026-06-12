from unittest.mock import MagicMock

import pytest

from src.model.item import Item as ItemDef, ItemEffect
from src.model.player import Item, PlayerPokemon, PlayerPokemonMove, PlayerProfile
from src.systems.bag_system import BagSystem


def make_item_def(effect_amount=20):
    effect = ItemEffect({"type": "heal", "amount": effect_amount})
    return ItemDef({"description": "Heals HP", "price": 300}, [effect])


def make_save_manager(pokemon_hp, pokemon_level=10, base_hp=50):
    """Build a mock SaveManager with one Pokémon at the given HP."""
    pokemon = PlayerPokemon(
        name="mudkip", hp=pokemon_hp, level=pokemon_level, exp=0,
        moves=[PlayerPokemonMove(name="tackle", pp=35)],
    )
    profile = PlayerProfile(
        pokemon=[pokemon],
        items=[Item(name="potion", count=3)],
        pokeballs=[Item(name="pokeball", count=2)],
    )
    sm = MagicMock()
    sm.player = profile
    sm.getPokemon.return_value = pokemon
    return sm


def make_data_loader(base_hp=50):
    dl = MagicMock()
    dl.get_pokemon.return_value.stats.hp = base_hp
    dl.get_item.return_value = make_item_def(effect_amount=20)
    return dl


def max_hp(base_hp, level):
    return ((2 * base_hp * level) // 100) + 5 + level


LEVEL = 50
BASE_HP = 50


def full_hp():
    return max_hp(BASE_HP, LEVEL)


# --- canUseItem ---

def test_can_use_item_true_when_damaged():
    hp = full_hp() - 30
    sm = make_save_manager(pokemon_hp=hp, pokemon_level=LEVEL, base_hp=BASE_HP)
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    assert system.canUseItem(0, "mudkip")


def test_can_use_item_false_at_full_hp():
    sm = make_save_manager(pokemon_hp=full_hp(), pokemon_level=LEVEL, base_hp=BASE_HP)
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    assert not system.canUseItem(0, "mudkip")


def test_can_use_item_false_empty_inventory():
    sm = make_save_manager(pokemon_hp=full_hp() - 10, pokemon_level=LEVEL)
    sm.player.items = []
    dl = make_data_loader()
    system = BagSystem(sm, dl)
    assert not system.canUseItem(0, "mudkip")


# --- useItem ---

def test_use_item_increases_hp_by_effect_amount():
    hp = full_hp() - 30
    sm = make_save_manager(pokemon_hp=hp, pokemon_level=LEVEL, base_hp=BASE_HP)
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    pokemon = sm.getPokemon.return_value
    hp_before = pokemon.hp
    system.useItem(0, "mudkip")
    assert pokemon.hp == hp_before + 20


def test_use_item_caps_hp_at_max():
    hp = full_hp() - 5
    sm = make_save_manager(pokemon_hp=hp, pokemon_level=LEVEL, base_hp=BASE_HP)
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    pokemon = sm.getPokemon.return_value
    system.useItem(0, "mudkip")
    assert pokemon.hp <= full_hp()


def test_use_item_decrements_count():
    hp = full_hp() - 20
    sm = make_save_manager(pokemon_hp=hp, pokemon_level=LEVEL, base_hp=BASE_HP)
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    system.useItem(0, "mudkip")
    assert sm.player.items[0].count == 2


def test_use_item_removes_item_when_count_hits_zero():
    hp = full_hp() - 20
    sm = make_save_manager(pokemon_hp=hp, pokemon_level=LEVEL, base_hp=BASE_HP)
    sm.player.items[0].count = 1
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    system.useItem(0, "mudkip")
    assert len(sm.player.items) == 0


def test_can_use_item_false_when_pokemon_fainted():
    sm = make_save_manager(pokemon_hp=0, pokemon_level=LEVEL, base_hp=BASE_HP)
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    assert not system.canUseItem(0, "mudkip")


def test_can_use_item_out_of_bounds_raises():
    sm = make_save_manager(pokemon_hp=full_hp() - 10, pokemon_level=LEVEL, base_hp=BASE_HP)
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    with pytest.raises(IndexError):
        system.canUseItem(99, "mudkip")


def test_get_pokeballs_returns_pokeball_list():
    sm = make_save_manager(pokemon_hp=full_hp(), pokemon_level=LEVEL)
    dl = make_data_loader()
    system = BagSystem(sm, dl)
    assert system.getPokeballs()[0].name == "pokeball"
