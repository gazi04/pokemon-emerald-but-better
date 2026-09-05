"""Sprite-path resolution with a placeholder fallback.

`arcade.load_texture` and `arcade.Sprite` both raise FileNotFoundError on a
missing path, so a species whose art has not been drawn yet used to crash the
renderer outright. Everything that loads a pokemon sprite goes through here
instead: a gap in the art becomes a question mark on screen, not a traceback.

Two entry points because arcade wants a *path* when constructing a Sprite and a
*texture* everywhere else.
"""

import os

import arcade

from src.core.logger import get_logger

log = get_logger(__name__)

MISSING_SPRITE = "assets/sprite/pokemon/question_mark.png"

# Paths already reported, so a sprite reloaded every frame warns once.
_warned: set[str] = set()


def resolve_sprite_path(path: str) -> str:
    """`path` if the file exists, else the placeholder sprite."""
    cleaned = path.strip()
    if cleaned and os.path.isfile(cleaned):
        return cleaned

    if cleaned not in _warned:
        _warned.add(cleaned)
        log.warning("Sprite not found, using placeholder: %s", cleaned or "<empty>")
    return MISSING_SPRITE


def load_sprite_texture(path: str) -> arcade.Texture:
    """Load `path` as a texture, falling back to the placeholder."""
    return arcade.load_texture(resolve_sprite_path(path))
