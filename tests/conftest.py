import os
import shutil
from pathlib import Path

import pytest

from src.core.data_loader import DataLoader
from src.core.event_bus import EventBus, global_bus
from src.core.save_manager import SaveManager
from src.model.player import Item, PlayerPokemon, PlayerPokemonMove, PlayerProfile, PlayerState

FIXTURE_DIR = Path(__file__).parent / "data"
PROJECT_DATA = Path(__file__).parent.parent / "data"


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def data_loader(tmp_path, monkeypatch):
    """DataLoader pointed at fixture data in a tmp working directory."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name in ("pokemon.json", "moves.json", "items.json"):
        shutil.copy(FIXTURE_DIR / name, data_dir / name)
    # util functions read types.json and encounters.json from cwd/data/
    for name in ("types.json", "encounters.json"):
        shutil.copy(PROJECT_DATA / name, data_dir / name)
    monkeypatch.chdir(tmp_path)
    return DataLoader()


@pytest.fixture
def save_manager(tmp_path, monkeypatch):
    """SaveManager with all file paths redirected to tmp_path."""
    monkeypatch.setattr("src.core.save_manager.SAVE_PATH", str(tmp_path / "save.json"))
    monkeypatch.setattr("src.core.save_manager.SAVE_TMP_PATH", str(tmp_path / "save.tmp.json"))
    monkeypatch.setattr("src.core.save_manager.SAVE_BAK_PATH", str(tmp_path / "save.bak.json"))
    monkeypatch.setattr("src.core.save_manager.DEFAULT_PATH", str(FIXTURE_DIR / "player_fixture.json"))
    return SaveManager()


@pytest.fixture
def player_state():
    return PlayerState(map_name="littleroot_town", grid_x=0, grid_y=0, pixel_x=0.0, pixel_y=0.0)


@pytest.fixture
def mudkip_pokemon():
    return PlayerPokemon(
        name="mudkip", hp=50, level=10, exp=0,
        moves=[PlayerPokemonMove(name="tackle", pp=35)],
    )


@pytest.fixture
def player_profile(mudkip_pokemon):
    return PlayerProfile(
        pokemon=[mudkip_pokemon],
        items=[Item(name="potion", count=3)],
        pokeballs=[Item(name="pokeball", count=5)],
    )


@pytest.fixture(autouse=True)
def reset_global_bus():
    """Clear global_bus subscribers before and after each test."""
    global_bus._subscribers.clear()
    yield
    global_bus._subscribers.clear()
