"""Contract tests over the real data/pokemon.json and assets/sprite/pokemon/.

Every other sprite test builds its own textures or mocks the loader, so nothing
proved the paths in pokemon.json point at files that exist. That gap let ten of
sixteen species ship with a front sprite that raises FileNotFoundError the
moment it is rendered: nine had their art saved as `<name>_back.png` inside
`front/`, so `<name>_front.png` never resolved, and lotad had no front art at
all.

These tests assert the declared paths and the files on disk agree.
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
POKEMON_PATH = REPO_ROOT / "data" / "pokemon.json"

# Species whose art genuinely does not exist yet, as opposed to being misnamed.
# `src.assets.resolve_sprite_path` renders these as question_mark.png instead of
# crashing (see test_falls_back_rather_than_crashing below). Drop a name from
# here the moment its art lands — test_known_gaps_are_still_gaps fails if this
# set names a file that now exists, so it cannot rot into a silent exemption.
MISSING_FRONT_ART = {"lotad"}


@pytest.fixture(scope="module")
def species() -> dict:
    with open(POKEMON_PATH) as f:
        return json.load(f)


def _sprite_paths(species: dict, side: str) -> list[tuple[str, str]]:
    return [(name, data["sprites"][side]) for name, data in species.items()]


@pytest.mark.parametrize("side", ["front", "back"])
def test_every_declared_sprite_file_exists(species, side):
    """The path in pokemon.json must resolve to a real file — arcade's loader
    raises FileNotFoundError rather than falling back."""
    exempt = MISSING_FRONT_ART if side == "front" else set()
    missing = [
        f"{name}: {path}"
        for name, path in _sprite_paths(species, side)
        if name not in exempt and not (REPO_ROOT / path).is_file()
    ]

    assert not missing, f"{len(missing)} missing {side} sprites:\n" + "\n".join(missing)


def test_known_gaps_are_still_gaps(species):
    """Keeps MISSING_FRONT_ART honest: once the art lands, this fails until the
    name is removed, so the exemption cannot outlive the gap it documents."""
    fixed = [
        name
        for name, path in _sprite_paths(species, "front")
        if name in MISSING_FRONT_ART and (REPO_ROOT / path).is_file()
    ]

    assert not fixed, (
        f"front art now exists for {fixed} — remove it from MISSING_FRONT_ART"
    )


@pytest.mark.parametrize("side", ["front", "back"])
def test_sprites_live_in_the_directory_for_their_side(species, side):
    """A front sprite under back/ (or vice versa) would load, but render the
    wrong pose — the failure mode that hid behind the missing files."""
    wrong = [
        f"{name}: {path}"
        for name, path in _sprite_paths(species, side)
        if f"/{side}/" not in path
    ]

    assert not wrong, f"{side} sprites outside the {side}/ directory:\n" + "\n".join(
        wrong
    )


def test_falls_back_rather_than_crashing(species):
    """Whatever is still missing must resolve to the placeholder, so a gap in
    the art is a wrong-looking sprite and never a crash."""
    from src.assets import MISSING_SPRITE, resolve_sprite_path

    for name, path in _sprite_paths(species, "front"):
        resolved = resolve_sprite_path(path)
        assert (REPO_ROOT / resolved).is_file(), f"{name} resolved to a missing file"
        if name in MISSING_FRONT_ART:
            assert resolved == MISSING_SPRITE
