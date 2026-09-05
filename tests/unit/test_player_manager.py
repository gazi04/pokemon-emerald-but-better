"""Tests for PlayerManager: the live-save-state wrapper around SaveManager."""

from unittest.mock import MagicMock

import pytest

from src.core.player_manager import PlayerManager
from src.model.save.npc_state import NPCState
from src.model.save.player import PlayerPokemon, PlayerPokemonMove


# --- money -------------------------------------------------------------


def test_add_money_increases_and_returns_total(player_manager):
    total = player_manager.add_money(50)
    assert total == 50
    assert player_manager.get_money() == 50


def test_remove_money_success(player_manager):
    player_manager.add_money(100)
    assert player_manager.remove_money(40) is True
    assert player_manager.get_money() == 60


def test_remove_money_fails_when_insufficient(player_manager):
    player_manager.add_money(10)
    assert player_manager.remove_money(20) is False
    assert player_manager.get_money() == 10


# --- heal_team -----------------------------------------------------------


def test_heal_team_restores_hp_and_pp(player_manager):
    mudkip = player_manager.get_pokemon("mudkip")
    mudkip.hp = 1
    mudkip.moves[0].pp = 0

    player_manager.heal_team()

    healed = player_manager.get_pokemon("mudkip")
    assert healed.hp > 1
    assert healed.moves[0].pp == 35  # tackle's max pp in fixture data


# --- status / level --------------------------------------------------------


def test_update_pokemon_status(player_manager):
    player_manager.update_pokemon_status("mudkip", "poison")
    assert player_manager.get_pokemon("mudkip").status_condition == "poison"

    player_manager.update_pokemon_status("mudkip", None)
    assert player_manager.get_pokemon("mudkip").status_condition is None


def test_update_level_without_evolution(player_manager):
    player_manager.update_level("mudkip", 12, 500)
    pokemon = player_manager.get_pokemon("mudkip")
    assert pokemon.level == 12
    assert pokemon.exp == 500
    assert pokemon.name == "mudkip"


def test_update_level_with_evolution_renames_pokemon(player_manager):
    player_manager.update_level("mudkip", 16, 1000, evolved_name="marshtomp")
    assert player_manager.get_pokemon("mudkip") is None
    evolved = player_manager.get_pokemon("marshtomp")
    assert evolved is not None
    assert evolved.level == 16


# --- learn_move --------------------------------------------------------------


def test_learn_move_appends_when_moveset_not_full(player_manager):
    player_manager.learn_move("mudkip", "growl")
    names = [m.name for m in player_manager.get_pokemon("mudkip").moves]
    assert names == ["tackle", "growl"]


def test_learn_move_noop_for_unknown_move(player_manager):
    player_manager.learn_move("mudkip", "not-a-real-move")
    names = [m.name for m in player_manager.get_pokemon("mudkip").moves]
    assert names == ["tackle"]


def test_learn_move_replaces_at_index_zero(player_manager):
    """Regression test: index=0 must trigger a replace, not be treated as falsy
    and silently skipped (index and 0 are both valid slot numbers)."""
    pokemon = player_manager.get_pokemon("mudkip")
    pokemon.moves = [
        PlayerPokemonMove(name="tackle", pp=35),
        PlayerPokemonMove(name="growl", pp=40),
        PlayerPokemonMove(name="ember", pp=25),
        PlayerPokemonMove(name="growl", pp=40),
    ]

    player_manager.learn_move("mudkip", "ember", index=0)

    assert player_manager.get_pokemon("mudkip").moves[0].name == "ember"


def test_learn_move_replaces_at_nonzero_index(player_manager):
    pokemon = player_manager.get_pokemon("mudkip")
    pokemon.moves = [
        PlayerPokemonMove(name="tackle", pp=35),
        PlayerPokemonMove(name="growl", pp=40),
        PlayerPokemonMove(name="ember", pp=25),
        PlayerPokemonMove(name="growl", pp=40),
    ]

    player_manager.learn_move("mudkip", "ember", index=2)

    assert player_manager.get_pokemon("mudkip").moves[2].name == "ember"


# --- held item / pokemon lookups --------------------------------------------


def test_update_pokemon_held_item_sets_item(player_manager):
    player_manager.update_pokemon_held_item("mudkip", "potion")
    assert player_manager.get_pokemon("mudkip").held_item == "potion"


def test_update_pokemon_held_item_raises_for_unknown_pokemon(player_manager):
    with pytest.raises(KeyError):
        player_manager.update_pokemon_held_item("nonexistent", "potion")


def test_add_pokemon_delegates_to_save(player_manager):
    new_pokemon = PlayerPokemon(
        name="torchic", hp=20, level=5, exp=0, ability="blaze", moves=[], held_item=None
    )
    # add_pokemon delegates to the save; with room in the party the new mon is
    # added there (a full party would overflow to a PC box instead).
    player_manager.add_pokemon(new_pokemon)
    assert player_manager.get_pokemon("torchic") is not None


def test_get_pokemon_team_returns_full_party(player_manager):
    team = player_manager.get_pokemon_team()
    assert [p.name for p in team] == ["mudkip"]


# --- seen / inventory --------------------------------------------------------


def test_mark_seen_and_get_seen_pokemon(player_manager):
    assert player_manager.get_seen_pokemon() == []
    player_manager.mark_seen("poochyena")
    assert player_manager.get_seen_pokemon() == ["poochyena"]


def test_mark_seen_normalizes_to_lowercase(player_manager):
    """The Pokédex tests membership against lowercase DataLoader keys, so a
    capitalized entry would render blank while still inflating the counter."""
    player_manager.mark_seen("Poochyena")
    assert player_manager.get_seen_pokemon() == ["poochyena"]


def test_mark_seen_dedupes_across_casing(player_manager):
    player_manager.mark_seen("Poochyena")
    player_manager.mark_seen("poochyena")
    player_manager.mark_seen("POOCHYENA")
    assert player_manager.get_seen_pokemon() == ["poochyena"]


def test_add_pokemon_records_species_lowercase_in_seen(player_manager):
    """add_pokemon is the second mark_seen writer and passes the name un-lowered."""
    player_manager.add_pokemon(
        PlayerPokemon(
            name="Zigzagoon",
            hp=20,
            level=5,
            exp=0,
            ability="pick_up",
            moves=[PlayerPokemonMove(name="tackle", pp=25)],
            held_item=None,
        )
    )
    assert player_manager.get_seen_pokemon() == ["zigzagoon"]


def test_add_item_increases_existing_stack(player_manager):
    player_manager.add_item("potion", 2)
    assert player_manager.get_inventory()["potion"].count == 5


def test_add_item_creates_new_stack(player_manager):
    player_manager.add_item("pokeball", 1)
    inventory = player_manager.get_inventory()
    assert inventory["pokeball"].count == 6


def test_consume_item_removes_stack_when_exhausted(player_manager):
    player_manager.get_inventory()["potion"].count = 1
    assert player_manager.consume_item("potion") is True
    assert "potion" not in player_manager.get_inventory()


def test_consume_item_returns_false_for_missing_item(player_manager):
    assert player_manager.consume_item("nonexistent") is False


# --- persist_active_pokemon --------------------------------------------------


def test_persist_active_pokemon_raises_when_evolved_without_evolution_data(
    player_manager,
):
    battle = MagicMock()
    battle.name = "mudkip"
    battle.current_hp = 10
    battle.status_effect = MagicMock(value=None)
    battle.moves = []
    battle.evolution = None

    with pytest.raises(ValueError, match="evolved but has no evolution data"):
        player_manager.persist_active_pokemon(battle, has_evolved=True)


# --- npc state capture/restore ------------------------------------------------


def test_init_loads_npc_states_when_present(data_loader):
    sm = MagicMock()
    sm.player.npc_states = [
        {"npc_id": "npc1", "has_talked": True, "has_fought": False, "defeated": False}
    ]
    pm = PlayerManager(sm, data_loader)
    assert pm.npc_manager.get_state("npc1").has_talked is True


def test_capture_npc_states_round_trips_through_save(data_loader):
    sm = MagicMock()
    sm.player.npc_states = []
    pm = PlayerManager(sm, data_loader)
    pm.npc_manager.get_state("npc1").has_talked = True

    pm.capture_npc_states()

    assert sm.player.npc_states == [NPCState(npc_id="npc1", has_talked=True).to_dict()]


# --- box storage -------------------------------------------------------
# X1: add_pokemon_box looped every box, `continue`d past full ones and appended
# to each remaining one without returning, so one caught Pokemon landed in ALL
# non-full boxes. The assertions below check the boxes that must stay EMPTY —
# asserting only that the target box received it would pass on the bug.


def _mon(name: str) -> PlayerPokemon:
    return PlayerPokemon(
        name=name,
        hp=10,
        level=5,
        exp=0,
        ability="",
        moves=[PlayerPokemonMove(name="tackle", pp=35)],
        held_item=None,
    )


def _fill_party(player_manager):
    player_manager.player.pokemon = [_mon(f"mon{i}") for i in range(6)]


def test_full_party_sends_the_catch_to_exactly_one_box(player_manager):
    from src.model.save.player import Box

    player_manager.player.boxs = [Box("Box 1", []), Box("Box 2", []), Box("Box 3", [])]
    _fill_party(player_manager)

    player_manager.add_pokemon(_mon("ralts"))

    stored = [len(box.pokemons) for box in player_manager.player.boxs]
    assert stored == [1, 0, 0], "the catch was duplicated across boxes"


def test_box_storage_fills_the_first_box_before_the_next(player_manager):
    from src.model.save.player import BOX_CAPACITY, Box

    first = Box("Box 1", [_mon(f"m{i}") for i in range(BOX_CAPACITY - 1)])
    second = Box("Box 2", [])
    player_manager.player.boxs = [first, second]
    _fill_party(player_manager)

    player_manager.add_pokemon(_mon("ralts"))
    assert (len(first.pokemons), len(second.pokemons)) == (BOX_CAPACITY, 0)

    player_manager.add_pokemon(_mon("zubat"))
    assert (len(first.pokemons), len(second.pokemons)) == (BOX_CAPACITY, 1)


def test_all_boxes_full_creates_a_new_one_rather_than_losing_the_catch(player_manager):
    from src.model.save.player import BOX_CAPACITY, Box

    player_manager.player.boxs = [
        Box("Box 1", [_mon(f"m{i}") for i in range(BOX_CAPACITY)])
    ]
    _fill_party(player_manager)

    player_manager.add_pokemon(_mon("ralts"))

    assert len(player_manager.player.boxs) == 2
    assert player_manager.player.boxs[1].name == "Box 2"
    assert [p.name for p in player_manager.player.boxs[1].pokemons] == ["ralts"]


def test_no_boxes_at_all_still_stores_the_catch(player_manager):
    """The shipped save has one box, but nothing guarantees that."""
    player_manager.player.boxs = []
    _fill_party(player_manager)

    assert player_manager.add_pokemon(_mon("ralts")) is True
    assert len(player_manager.player.boxs) == 1
    assert [p.name for p in player_manager.player.boxs[0].pokemons] == ["ralts"]


def test_room_in_the_party_skips_the_boxes_entirely(player_manager):
    from src.model.save.player import Box

    player_manager.player.boxs = [Box("Box 1", [])]
    before = len(player_manager.player.pokemon)

    assert player_manager.add_pokemon(_mon("ralts")) is True

    assert len(player_manager.player.pokemon) == before + 1
    assert player_manager.player.boxs[0].pokemons == []


# --- owned species -----------------------------------------------------
# L4: the Pokedex built `owned` from the party alone, so a boxed species showed
# as merely seen. The box assertions are the regression.


def test_owned_includes_the_party(player_manager):
    player_manager.player.pokemon = [_mon("mudkip")]

    assert player_manager.get_owned_pokemon() == {"mudkip"}


def test_owned_includes_boxed_pokemon(player_manager):
    from src.model.save.player import Box

    player_manager.player.pokemon = [_mon("mudkip")]
    player_manager.player.boxs = [Box("Box 1", [_mon("ralts")])]

    assert player_manager.get_owned_pokemon() == {"mudkip", "ralts"}


def test_owned_spans_every_box(player_manager):
    from src.model.save.player import Box

    player_manager.player.pokemon = []
    player_manager.player.boxs = [
        Box("Box 1", [_mon("ralts")]),
        Box("Box 2", [_mon("zubat")]),
    ]

    assert player_manager.get_owned_pokemon() == {"ralts", "zubat"}
