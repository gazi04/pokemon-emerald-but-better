"""Battle-wide weather: what's falling, for how long, and what it does.

Owned by BattleSystem (weather is a property of the battle, not of a Pokémon).
Pure bookkeeping + rules — it never touches a BattlePokemon; the system reads
these helpers and applies the results, mirroring how combat_calculator stays
free of battle objects.
"""

from dataclasses import dataclass

from src.enums.weather import Weather

DEFAULT_DURATION = 5
# Sandstorm/hail chip: 1/16 of max HP per turn.
RESIDUAL_DIVISOR = 16

# Types that shrug off each weather's residual damage.
_SANDSTORM_IMMUNE_TYPES = frozenset({"rock", "ground", "steel"})
_HAIL_IMMUNE_TYPES = frozenset({"ice"})

_START = {
    Weather.SUN: "The sunlight turned harsh!",
    Weather.RAIN: "It started to rain!",
    Weather.SANDSTORM: "A sandstorm kicked up!",
    Weather.HAIL: "It started to hail!",
}
_ONGOING = {
    Weather.SANDSTORM: "The sandstorm rages.",
    Weather.HAIL: "The hail crashes down.",
}
_END = {
    Weather.SUN: "The harsh sunlight faded.",
    Weather.RAIN: "The rain stopped.",
    Weather.SANDSTORM: "The sandstorm subsided.",
    Weather.HAIL: "The hail stopped.",
}
_RESIDUAL = {
    Weather.SANDSTORM: "{name} is buffeted by the sandstorm!",
    Weather.HAIL: "{name} is pelted by hail!",
}


@dataclass
class WeatherState:
    kind: Weather = Weather.NONE
    turns_left: int = 0

    @property
    def is_active(self) -> bool:
        return self.kind != Weather.NONE

    def set(self, kind: Weather, turns: int = DEFAULT_DURATION) -> list[str]:
        """Start a weather. Re-summoning the same weather fails, as in the games."""
        if kind == Weather.NONE:
            return []
        if kind == self.kind:
            return ["But it failed!"]
        self.kind = kind
        self.turns_left = turns
        return [_START.get(kind, "")]

    def clear(self) -> None:
        self.kind = Weather.NONE
        self.turns_left = 0

    # --- combat effects -------------------------------------------------

    def damage_multiplier(self, move_type: str) -> float:
        """How this weather scales a move's damage by its type.

        Rain boosts Water and damps Fire; harsh sun does the reverse.
        """
        if self.kind == Weather.RAIN:
            if move_type == "water":
                return 1.5
            if move_type == "fire":
                return 0.5
        elif self.kind == Weather.SUN:
            if move_type == "fire":
                return 1.5
            if move_type == "water":
                return 0.5
        return 1.0

    def damages(self, types: list[str]) -> bool:
        """Whether a Pokémon of these types takes residual chip this turn."""
        if self.kind == Weather.SANDSTORM:
            return not _SANDSTORM_IMMUNE_TYPES.intersection(types)
        if self.kind == Weather.HAIL:
            return not _HAIL_IMMUNE_TYPES.intersection(types)
        return False

    def residual_damage(self, max_hp: int) -> int:
        return max(1, max_hp // RESIDUAL_DIVISOR)

    def residual_message(self, name: str) -> str:
        template = _RESIDUAL.get(self.kind)
        return template.format(name=name) if template else ""

    # --- duration -------------------------------------------------------

    def tick(self) -> list[str]:
        """Count down one turn. Returns the ongoing line, or the end line when
        the weather runs out (and clears itself)."""
        if not self.is_active:
            return []
        self.turns_left -= 1
        if self.turns_left <= 0:
            ended = _END.get(self.kind, "")
            self.clear()
            return [ended] if ended else []
        ongoing = _ONGOING.get(self.kind)
        return [ongoing] if ongoing else []
