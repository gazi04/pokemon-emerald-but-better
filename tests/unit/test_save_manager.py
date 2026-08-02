import json

import pytest

from src.core.player_serializer import PlayerSerializer
from src.model.motion.player_motion import PlayerMotion


# --- deserialize ---


def test_parse_player_pokemon_name(save_manager):
    assert save_manager.player.pokemon[0].name == "mudkip"


def test_parse_player_pokemon_level(save_manager):
    assert save_manager.player.pokemon[0].level == 10


def test_parse_player_pokemon_hp(save_manager):
    assert save_manager.player.pokemon[0].hp == 50


def test_parse_player_move_name(save_manager):
    assert save_manager.player.pokemon[0].moves[0].name == "tackle"


def test_parse_player_move_pp(save_manager):
    assert save_manager.player.pokemon[0].moves[0].pp == 35


def test_parse_player_items(save_manager):
    # items is now a dict keyed by item id
    assert save_manager.player.items["potion"].count == 3


def test_parse_player_pokeballs(save_manager):
    # pokeballs are just items in the "pokeball" category
    assert save_manager.player.items["pokeball"].count == 5


# --- serialize round-trip ---


def test_deparse_player_round_trip(save_manager):
    original_name = save_manager.player.pokemon[0].name
    data = PlayerSerializer.serialize(save_manager.player)
    re_parsed = PlayerSerializer.deserialize(data)
    assert re_parsed.pokemon[0].name == original_name
    assert re_parsed.pokemon[0].level == save_manager.player.pokemon[0].level
    assert (
        re_parsed.pokemon[0].moves[0].name
        == save_manager.player.pokemon[0].moves[0].name
    )


# --- get_pokemon ---


def test_get_pokemon_found(save_manager):
    result = save_manager.player.get_pokemon("mudkip")
    assert result is not None
    assert result.name == "mudkip"


def test_get_pokemon_not_found_returns_none(save_manager):
    assert save_manager.player.get_pokemon("nonexistent") is None


# --- update_hp ---


def test_update_hp_normal(save_manager):
    save_manager.player.update_hp("mudkip", 20)
    assert save_manager.player.get_pokemon("mudkip").hp == 20


def test_update_hp_clamps_to_zero(save_manager):
    save_manager.player.update_hp("mudkip", -10)
    assert save_manager.player.get_pokemon("mudkip").hp == 0


def test_update_hp_unknown_pokemon_does_not_crash(save_manager):
    save_manager.player.update_hp("unknown", 10)  # no error


# --- update_move_pp ---


def test_update_move_pp(save_manager):
    save_manager.player.update_move_pp("mudkip", "tackle", 5)
    assert save_manager.player.get_pokemon("mudkip").moves[0].pp == 5


# --- update_level ---


def test_update_level(save_manager):
    save_manager.player.update_level("mudkip", 15, 200)
    pokemon = save_manager.player.get_pokemon("mudkip")
    assert pokemon.level == 15
    assert pokemon.exp == 200


def test_update_level_with_evolution_changes_name(save_manager):
    save_manager.player.update_level("mudkip", 16, 0, evolved_name="marshtomp")
    pokemon = save_manager.player.get_pokemon("marshtomp")
    assert pokemon is not None
    assert pokemon.level == 16


# --- flush_save (replaces compile_save_state tests) ---


def test_flush_save_writes_position(save_manager, tmp_path):
    state = PlayerMotion(
        map_name="route_101", direction="up", pixel_x=64.0, pixel_y=128.0
    )
    save_manager.flush_save(state)
    data = json.loads((tmp_path / "save.json").read_text())
    assert data["position"]["map_name"] == "route_101"
    assert data["position"]["direction"] == "up"
    assert data["position"]["pixel_x"] == 64.0


def test_flush_save_writes_pokemons(save_manager, tmp_path):
    state = PlayerMotion()
    save_manager.flush_save(state)
    data = json.loads((tmp_path / "save.json").read_text())
    assert len(data["pokemons"]) == 1
    assert data["pokemons"][0]["name"] == "mudkip"


# --- flush_save + reload ---


def test_flush_save_creates_file(save_manager, tmp_path):
    state = PlayerMotion(
        map_name="test_map", direction="right", pixel_x=10.0, pixel_y=20.0
    )
    result = save_manager.flush_save(state)
    assert result is True
    assert (tmp_path / "save.json").exists()


def test_flush_save_and_reload_preserves_state(save_manager, tmp_path, monkeypatch):
    save_manager.player.update_hp("mudkip", 30)
    state = PlayerMotion(
        map_name="littleroot_town", direction="down", pixel_x=5.0, pixel_y=5.0
    )
    save_manager.flush_save(state)

    monkeypatch.setattr("src.core.save_manager.SAVE_PATH", str(tmp_path / "save.json"))
    from src.core.save_manager import SaveManager as SM2

    sm2 = SM2()
    mudkip = sm2.player.get_pokemon("mudkip")
    assert mudkip is not None
    assert mudkip.hp == 30


def test_flush_save_succeeds_when_backup_copy_fails(
    save_manager, tmp_path, monkeypatch
):
    """A failing backup copy must not block promoting the new save."""
    state = PlayerMotion(
        map_name="oldale_town", direction="down", pixel_x=1.0, pixel_y=2.0
    )
    # First flush creates save.json so the backup branch (copy2) is
    # actually exercised on the second flush below.
    save_manager.flush_save(state)

    def _raise(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("src.core.save_manager.shutil.copy2", _raise)

    state2 = PlayerMotion(
        map_name="petalburg_city", direction="up", pixel_x=3.0, pixel_y=4.0
    )
    result = save_manager.flush_save(state2)

    assert result is True
    data = json.loads((tmp_path / "save.json").read_text())
    assert data["position"]["map_name"] == "petalburg_city"


def test_missing_save_json_falls_back_to_default(save_manager):
    assert save_manager.player is not None
    assert save_manager.player.pokemon[0].name == "mudkip"


def test_parse_player_multi_pokemon(save_manager):
    data = {
        "pokemons": [
            {
                "name": "mudkip",
                "hp": 50,
                "level": 10,
                "exp": 0,
                "ability": "torrent",
                "held_item": None,
                "moves": [{"name": "tackle", "pp": 35}],
            },
            {
                "name": "treecko",
                "hp": 45,
                "level": 8,
                "exp": 0,
                "ability": "overgrow",
                "held_item": None,
                "moves": [{"name": "growl", "pp": 40}],
            },
        ],
        "items": {},
    }
    profile = PlayerSerializer.deserialize(data)
    assert len(profile.pokemon) == 2
    assert profile.pokemon[1].name == "treecko"
    assert profile.pokemon[1].moves[0].name == "growl"


def test_update_move_unknown_move_name_no_crash(save_manager):
    save_manager.player.update_move_pp("mudkip", "hyperbeam", 5)
    assert save_manager.player.get_pokemon("mudkip").moves[0].pp == 35


def test_load_corrupted_save_falls_back(tmp_path, monkeypatch):
    """A corrupt save.json must not brick startup — fall back to the default."""
    corrupt = tmp_path / "save.json"
    corrupt.write_text("{not valid json}")
    monkeypatch.setattr("src.core.save_manager.SAVE_PATH", str(corrupt))
    monkeypatch.setattr(
        "src.core.save_manager.SAVE_BAK_PATH", str(tmp_path / "missing_bak.json")
    )
    # DEFAULT_PATH stays the shipped data/player.json (valid baseline)
    from src.core.save_manager import SaveManager as SM2

    sm = SM2()  # must NOT raise
    assert sm.player is not None


def test_load_all_sources_unreadable_raises(tmp_path, monkeypatch):
    """If save, backup, and default are all unreadable, loading raises."""
    corrupt = tmp_path / "save.json"
    corrupt.write_text("{not valid json}")
    monkeypatch.setattr("src.core.save_manager.SAVE_PATH", str(corrupt))
    monkeypatch.setattr(
        "src.core.save_manager.SAVE_BAK_PATH", str(tmp_path / "missing_bak.json")
    )
    monkeypatch.setattr(
        "src.core.save_manager.DEFAULT_PATH", str(tmp_path / "missing.json")
    )
    from src.core.save_manager import SaveManager as SM2

    with pytest.raises(RuntimeError):
        SM2()
