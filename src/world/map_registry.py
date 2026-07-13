"""Resolves stable map IDs to .tmx file paths and back.

A *map id* is the map's path under `maps_dir`, without the extension
(e.g. "oldale_town/pokemon_center"). Convention-first, so scaling to hundreds
of maps needs zero per-map registration. An optional `aliases` table maps
friendly names — fly destinations, story spots — onto real ids without any
caller knowing the difference.
"""

from typing import Optional

from src.core.logger import get_logger

log = get_logger(__name__)


class MapRegistry:
    def __init__(
        self,
        maps_dir: str = "assets/map",
        aliases: Optional[dict[str, str]] = None,
    ):
        self._maps_dir = maps_dir.replace("\\", "/").rstrip("/")
        self._aliases = aliases or {}

    def resolve(self, map_ref: str) -> str:
        """Normalise any reference (id, alias, or full path) to a canonical id."""
        map_ref = self._aliases.get(map_ref, map_ref)
        return self.id_from_path(map_ref)

    def path_for(self, map_ref: str) -> str:
        """The .tmx path for a map reference (no hardcoded paths at call sites)."""
        return f"{self._maps_dir}/{self.resolve(map_ref)}.tmx"

    def id_from_path(self, value: str) -> str:
        """Idempotent: accepts a full .tmx path or an already-clean id."""
        p = value.replace("\\", "/")
        prefix = self._maps_dir + "/"
        if p.startswith(prefix):
            p = p[len(prefix):]
        if p.endswith(".tmx"):
            p = p[:-4]
        return p

    def register_alias(self, alias: str, map_id: str) -> None:
        """Add a friendly alias (e.g. a fly destination) → real map id."""
        self._aliases[alias] = map_id
