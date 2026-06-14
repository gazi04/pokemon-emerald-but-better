import pytest


def test_get_pokemon_returns_correct_types(data_loader):
    profile = data_loader.get_pokemon("treecko")
    assert profile is not None
    assert "grass" in profile.types


def test_get_pokemon_returns_correct_stats(data_loader):
    profile = data_loader.get_pokemon("mudkip")
    assert profile.stats.hp == 50
    assert profile.stats.attack == 70


def test_get_pokemon_unknown_returns_none(data_loader):
    assert data_loader.get_pokemon("fakemon") is None


def test_get_pokemon_with_evolution(data_loader):
    profile = data_loader.get_pokemon("torchic")
    assert profile.evolution is not None
    assert profile.evolution.to == "combusken"
    assert profile.evolution.levelCap == 16


def test_get_pokemon_no_evolution(data_loader):
    profile = data_loader.get_pokemon("treecko")
    assert profile.evolution is None


def test_get_pokemon_sprites_loaded(data_loader):
    profile = data_loader.get_pokemon("treecko")
    assert profile.sprites.front != ""
    assert profile.sprites.back != ""


def test_get_move_tackle(data_loader):
    move = data_loader.get_move("tackle")
    assert move is not None
    assert move.power == 40
    assert move.category == "physical"
    assert move.type == "normal"
    assert move.accuracy == 100


def test_get_move_with_effects(data_loader):
    move = data_loader.get_move("close combat")
    assert len(move.effects) == 2


def test_get_move_status_move(data_loader):
    move = data_loader.get_move("growl")
    assert move.category == "status"
    assert move.power is None


def test_get_move_unknown_returns_none(data_loader):
    assert data_loader.get_move("hyper beam") is None


def test_get_item_potion(data_loader):
    item = data_loader.get_item("potion")
    assert item is not None
    assert item.effects[0].type == "heal"
    assert item.effects[0].amount == 20


def test_get_item_unknown_returns_none(data_loader):
    assert data_loader.get_item("master ball") is None
