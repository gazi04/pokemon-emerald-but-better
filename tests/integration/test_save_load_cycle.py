"""
Integration test: full save → disk → reload cycle via SaveManager.
"""

import pytest

from src.model.motion.player_motion import PlayerMotion


def test_save_load_preserves_hp(save_manager, tmp_path, monkeypatch):
    save_manager.player.update_hp("mudkip", 15)
    state = PlayerMotion(
        map_name="route_101", direction="left", pixel_x=100.0, pixel_y=200.0
    )
    assert save_manager.flush_save(state)

    monkeypatch.setattr("src.core.save_manager.SAVE_PATH", str(tmp_path / "save.json"))
    from src.core.save_manager import SaveManager

    reloaded = SaveManager()
    assert reloaded.player.get_pokemon("mudkip").hp == 15


def test_save_load_preserves_level_and_exp(save_manager, tmp_path, monkeypatch):
    save_manager.player.update_level("mudkip", 20, 500)
    state = PlayerMotion()
    save_manager.flush_save(state)

    monkeypatch.setattr("src.core.save_manager.SAVE_PATH", str(tmp_path / "save.json"))
    from src.core.save_manager import SaveManager

    reloaded = SaveManager()
    pokemon = reloaded.player.get_pokemon("mudkip")
    assert pokemon.level == 20
    assert pokemon.exp == 500


def test_save_load_preserves_move_pp(save_manager, tmp_path, monkeypatch):
    save_manager.player.update_move_pp("mudkip", "tackle", 10)
    state = PlayerMotion()
    save_manager.flush_save(state)

    monkeypatch.setattr("src.core.save_manager.SAVE_PATH", str(tmp_path / "save.json"))
    from src.core.save_manager import SaveManager

    reloaded = SaveManager()
    pokemon = reloaded.player.get_pokemon("mudkip")
    assert pokemon.moves[0].pp == 10


def test_save_load_preserves_position(save_manager, tmp_path, monkeypatch):
    state = PlayerMotion(
        map_name="littleroot_town", direction="up", pixel_x=256.0, pixel_y=512.0
    )
    save_manager.flush_save(state)

    monkeypatch.setattr("src.core.save_manager.SAVE_PATH", str(tmp_path / "save.json"))
    from src.core.save_manager import SaveManager

    reloaded = SaveManager()
    assert reloaded.saved_position["map_name"] == "littleroot_town"
    assert reloaded.saved_position["direction"] == "up"
    assert reloaded.saved_position["pixel_x"] == 256.0


def test_save_creates_backup_file(save_manager, tmp_path):
    state = PlayerMotion()
    save_manager.flush_save(state)  # first save (no backup yet)
    save_manager.flush_save(state)  # second save (backup should appear)
    assert (tmp_path / "save.bak.json").exists()


def test_double_save_both_files_valid_json(save_manager, tmp_path):
    import json

    state = PlayerMotion()
    save_manager.flush_save(state)
    save_manager.flush_save(state)
    with open(tmp_path / "save.json") as f:
        data = json.load(f)
    assert "pokemons" in data
    assert "items" in data


def test_flush_save_returns_true_on_success(save_manager):
    state = PlayerMotion()
    assert save_manager.flush_save(state) is True


def test_save_load_preserves_money(save_manager, tmp_path, monkeypatch):
    save_manager.player.money = 4242
    state = PlayerMotion()
    save_manager.flush_save(state)

    monkeypatch.setattr("src.core.save_manager.SAVE_PATH", str(tmp_path / "save.json"))
    from src.core.save_manager import SaveManager

    reloaded = SaveManager()
    assert reloaded.player.money == 4242


def test_save_load_preserves_npc_states(save_manager, tmp_path, monkeypatch):
    save_manager.player.npc_states = [
        {"npc_id": "rival", "has_talked": True, "has_fought": True, "defeated": True}
    ]
    state = PlayerMotion()
    save_manager.flush_save(state)

    monkeypatch.setattr("src.core.save_manager.SAVE_PATH", str(tmp_path / "save.json"))
    from src.core.save_manager import SaveManager

    reloaded = SaveManager()
    assert reloaded.player.npc_states == [
        {"npc_id": "rival", "has_talked": True, "has_fought": True, "defeated": True}
    ]


def test_new_game_loads_money_from_player_json(tmp_path, monkeypatch):
    # No save.json and no backup → SaveManager falls back to data/player.json (money: 1000)
    monkeypatch.setattr("src.core.save_manager.SAVE_PATH", str(tmp_path / "save.json"))
    monkeypatch.setattr(
        "src.core.save_manager.SAVE_BAK_PATH", str(tmp_path / "save.bak.json")
    )
    from src.core.save_manager import SaveManager

    fresh = SaveManager()
    assert fresh.player.money == 1000
