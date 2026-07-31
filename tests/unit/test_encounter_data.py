"""Contract tests over the real data/ and assets/map/ files.

`test_encounter_system.py` stubs the encounter table, so it can only prove the
lookup logic — never that the ids it looks up actually exist. That gap let Route
101 ship with 91 walkable bush tiles and zero encounters: the map id is `root101`
(the .tmx filename) while the table was keyed `route_101`, and EncounterSystem's
missing-table guard swallowed the miss silently.

These tests assert the two id spaces agree, using the real MapRegistry rather
than restating its rules.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from src.world.map_registry import MapRegistry

REPO_ROOT = Path(__file__).resolve().parents[2]
MAPS_DIR = REPO_ROOT / "assets" / "map"
ENCOUNTERS_PATH = REPO_ROOT / "data" / "encounters.json"
POKEMON_PATH = REPO_ROOT / "data" / "pokemon.json"

# Tiled stores tileset templates under assets/map/tilesets/; they are not
# playable maps and never become a map id.
EXCLUDED_DIRS = {"tilesets"}


def _load(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def encounters() -> dict:
    return _load(ENCOUNTERS_PATH)


@pytest.fixture(scope="module")
def registry() -> MapRegistry:
    """The real registry, pointed at the real maps dir — same id rules the game
    uses at runtime via MapManager."""
    return MapRegistry(str(MAPS_DIR))


def _playable_maps() -> list[Path]:
    return sorted(
        p
        for p in MAPS_DIR.rglob("*.tmx")
        if not EXCLUDED_DIRS.intersection(p.relative_to(MAPS_DIR).parts)
    )


def _bush_tile_count(tmx_path: Path) -> int:
    """Non-empty tiles on the layer named 'bush'.

    Mirrors what MapLoader._extract_bush_tiles ends up with, but reads the XML
    directly — the real parser needs an arcade.Scene (and therefore a GL
    context), which a data-only test should not require.
    """
    root = ET.parse(tmx_path).getroot()
    for layer in root.findall("layer"):
        if layer.get("name") != "bush":
            continue
        data = layer.find("data")
        if data is None or not data.text:
            return 0
        return sum(
            1 for gid in data.text.replace("\n", "").split(",") if gid.strip("0 ")
        )
    return 0


def _map_ids_with_bush() -> list[str]:
    # MAPS_DIR is absolute, so feed id_from_path absolute paths — its prefix
    # strip only fires when the two agree.
    registry = MapRegistry(str(MAPS_DIR))
    return [
        registry.id_from_path(str(p))
        for p in _playable_maps()
        if _bush_tile_count(p) > 0
    ]


# --- encounters.json keys must be real map ids --------------------------------


@pytest.mark.parametrize("map_id", sorted(_load(ENCOUNTERS_PATH).keys()))
def test_every_encounter_key_is_an_existing_map(map_id, registry):
    """A key that isn't a real map id is dead data: EncounterSystem's
    `if not table: return` guard hides the miss, so the table never fires."""
    tmx = Path(registry.path_for(map_id))
    assert tmx.is_file(), (
        f"encounters.json key '{map_id}' resolves to {tmx}, which does not exist. "
        f"Keys must be map ids — the .tmx path under assets/map/ without the "
        f"extension."
    )


# --- walkable grass must be able to spawn something --------------------------


@pytest.mark.parametrize("map_id", _map_ids_with_bush())
def test_every_map_with_bush_tiles_has_an_encounter_table(map_id, encounters):
    """The Route 101 regression, stated in the direction that matters: if the
    player can walk in tall grass there, something must be able to appear."""
    assert map_id in encounters, (
        f"map '{map_id}' has bush tiles but no encounters.json entry — walking "
        f"its grass will never trigger an encounter."
    )


def test_bush_map_discovery_is_not_vacuous():
    """Guards the test above: if the .tmx layout changes so no bush layer is
    found, the parametrize list would empty out and silently assert nothing."""
    assert _map_ids_with_bush(), "found no maps with bush tiles — parser is broken"


# --- table contents must be loadable -----------------------------------------


def test_every_encounter_species_exists_in_pokemon_json(encounters):
    """Once a table starts resolving, DataLoader.require_pokemon will raise on an
    unknown species — so a typo here turns a silent miss into a hard crash."""
    species = set(_load(POKEMON_PATH))
    missing = {
        entry["name"]
        for table in encounters.values()
        for entry in table.get("grass", [])
        if entry["name"] not in species
    }
    assert not missing, f"encounters.json references unknown species: {sorted(missing)}"


def test_every_encounter_table_has_a_usable_grass_list(encounters):
    """An entry with no grass list is inert; catching it here is cheaper than
    relying on the runtime guard."""
    empty = [map_id for map_id, table in encounters.items() if not table.get("grass")]
    assert not empty, f"encounters.json entries with no grass list: {empty}"
