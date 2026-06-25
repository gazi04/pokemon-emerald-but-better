from unittest.mock import MagicMock

import pytest

from src.model.static.item import ItemSpecies, ItemEffect
from src.model.save.player import ItemStack, PlayerPokemon, PlayerPokemonMove, PlayerSave
from src.systems.bag_system import BagSystem


def make_item_def(effect_amount=20):
    effect = ItemEffect(type="heal", amount=effect_amount)
    return ItemSpecies(description="Heals HP", price=300, effects=[effect])


def make_save_manager(pokemon_hp, pokemon_level=10, base_hp=50):
    """Build a mock SaveManager with one Pokémon at the given HP."""
    pokemon = PlayerPokemon(
        name="mudkip",
        hp=pokemon_hp,
        level=pokemon_level,
        exp=0,
        moves=[PlayerPokemonMove(name="tackle", pp=35)],
    )
    profile = PlayerSave(
        pokemon=[pokemon],
        items=[ItemStack(name="potion", count=3)],
        pokeballs=[ItemStack(name="pokeball", count=2)],
    )
    sm = MagicMock()
    sm.player = profile
    sm.getPokemon.return_value = pokemon
    # Route the mutation door to the real PlayerSave so the bag goes through
    # PlayerManager (the single door) while tests still assert on `profile`.
    sm.update_pokemon_hp.side_effect = profile.update_hp
    sm.consume_item.side_effect = profile.consume_item
    sm.consume_pokeball.side_effect = profile.consume_pokeball
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


# --- can_use_item ---


def test_can_use_item_true_when_damaged():
    hp = full_hp() - 30
    sm = make_save_manager(pokemon_hp=hp, pokemon_level=LEVEL, base_hp=BASE_HP)
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    assert system.can_use_item(0, "mudkip")


def test_can_use_item_false_at_full_hp():
    sm = make_save_manager(pokemon_hp=full_hp(), pokemon_level=LEVEL, base_hp=BASE_HP)
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    assert not system.can_use_item(0, "mudkip")


def test_can_use_item_false_empty_inventory():
    sm = make_save_manager(pokemon_hp=full_hp() - 10, pokemon_level=LEVEL)
    sm.player.items = []
    dl = make_data_loader()
    system = BagSystem(sm, dl)
    assert not system.can_use_item(0, "mudkip")


# --- use_item ---


def test_use_item_increases_hp_by_effect_amount():
    hp = full_hp() - 30
    sm = make_save_manager(pokemon_hp=hp, pokemon_level=LEVEL, base_hp=BASE_HP)
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    pokemon = sm.getPokemon.return_value
    hp_before = pokemon.hp
    system.use_item(0, "mudkip")
    assert pokemon.hp == hp_before + 20


def test_use_item_caps_hp_at_max():
    hp = full_hp() - 5
    sm = make_save_manager(pokemon_hp=hp, pokemon_level=LEVEL, base_hp=BASE_HP)
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    pokemon = sm.getPokemon.return_value
    system.use_item(0, "mudkip")
    assert pokemon.hp <= full_hp()


def test_use_item_decrements_count():
    hp = full_hp() - 20
    sm = make_save_manager(pokemon_hp=hp, pokemon_level=LEVEL, base_hp=BASE_HP)
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    system.use_item(0, "mudkip")
    assert sm.player.items[0].count == 2


def test_use_item_removes_item_when_count_hits_zero():
    hp = full_hp() - 20
    sm = make_save_manager(pokemon_hp=hp, pokemon_level=LEVEL, base_hp=BASE_HP)
    sm.player.items[0].count = 1
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    system.use_item(0, "mudkip")
    assert len(sm.player.items) == 0


def test_can_use_item_false_when_pokemon_fainted():
    sm = make_save_manager(pokemon_hp=0, pokemon_level=LEVEL, base_hp=BASE_HP)
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    assert not system.can_use_item(0, "mudkip")


def test_can_use_item_out_of_bounds_raises():
    sm = make_save_manager(
        pokemon_hp=full_hp() - 10, pokemon_level=LEVEL, base_hp=BASE_HP
    )
    dl = make_data_loader(base_hp=BASE_HP)
    system = BagSystem(sm, dl)
    with pytest.raises(IndexError):
        system.can_use_item(99, "mudkip")


def test_use_item_ignores_unknown_effect_type():
    # An effect type with no registered applier is skipped: no heal, but the
    # item is still consumed (matches the pre-dispatch behaviour).
    hp = full_hp() - 30
    sm = make_save_manager(pokemon_hp=hp, pokemon_level=LEVEL, base_hp=BASE_HP)
    dl = make_data_loader(base_hp=BASE_HP)
    dl.get_item.return_value = ItemSpecies(
        description="X", price=0, effects=[ItemEffect(type="stat", amount=1)]
    )
    system = BagSystem(sm, dl)
    pokemon = sm.getPokemon.return_value
    hp_before = pokemon.hp
    system.use_item(0, "mudkip")
    assert pokemon.hp == hp_before
    assert sm.player.items[0].count == 2


def test_get_pokeballs_returns_pokeball_list():
    sm = make_save_manager(pokemon_hp=full_hp(), pokemon_level=LEVEL)
    dl = make_data_loader()
    system = BagSystem(sm, dl)
    assert system.get_pokeballs()[0].name == "pokeball"
