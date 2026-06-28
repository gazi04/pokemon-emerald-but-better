from dataclasses import dataclass, field
from typing import Callable

@dataclass
class AbilityEffect:
    trigger: str        # "on_attack" | "on_hit" | "on_turn_end" | "on_switch_in" | "on_weather"
    type: str           # "stat_boost" | "status" | "damage" | "immunity" | "weather"
    target: str         # "self" | "enemy"
    stat: str | None = None
    change: int | None = None
    condition: str | None = None   # e.g. "paralysis", "burn" — triggers only under this condition
    chance: float | None = None    # 0.0 - 1.0, None means always

@dataclass
class Ability:
    name: str
    description: str
    effects: list[AbilityEffect] = field(default_factory=list)

    def __init__(self, data: dict):
        self.name = data["name"]
        self.description = data["description"]
        self.effects = [AbilityEffect(**e) for e in data.get("effects", [])]