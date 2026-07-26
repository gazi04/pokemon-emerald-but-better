"""The data-driven transition schema, decoupled from any controller/view.

A transition (authored in a Tiled `transitions` object layer) says where to go
and where to land. Landing is either a *named spawn* on the target map
(preferred) or an explicit world position (legacy). Unknown properties are kept
so future features (warp SFX, required story flags, one-way doors) can read them
without changing this parser.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Transition:
    target_map: str
    target_spawn: str | None = None
    target_position: tuple[float, float] | None = None
    properties: dict = field(default_factory=dict)

    @property
    def spawn(self):
        """The value to pass to MapManager: a spawn name, an (x, y), or None."""
        return self.target_spawn if self.target_spawn else self.target_position


# Canonical + legacy property keys, so existing maps keep working.
_MAP_KEYS = ("target_map", "destination map")


def parse_transition(properties: dict) -> Transition:
    target_map = _first(properties, _MAP_KEYS)
    if not target_map:
        raise KeyError(
            f"Transition is missing 'target_map' (or legacy 'destination map'); "
            f"got {list(properties)}"
        )

    spawn = properties.get("target_spawn")
    position: tuple[float, float] | None = None
    if spawn is None and "x" in properties and "y" in properties:
        position = (float(properties["x"]), float(properties["y"]))

    return Transition(
        target_map=target_map,
        target_spawn=spawn,
        target_position=position,
        properties=dict(properties),
    )


def _first(properties: dict, keys) -> str | None:
    for key in keys:
        if properties.get(key):
            return properties[key]
    return None
