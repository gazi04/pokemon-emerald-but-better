from dataclasses import dataclass, field
from typing import Callable

@dataclass
class AbilityEffect:
    trigger: str        # "on_attack" | "on_hit" | "on_turn_end" | "on_switch_in" | "on_weather"
    type: str           # "stat_boost" | "status" | "damage" | "immunity" | "heal"
    target: str         # "self" | "enemy"
    move_type: str | None = None     # only apply if the move matches this type
    stat: str | None = None
    change: int | None = None
    condition: str | None = None   # trigger gate, e.g. "low_hp" | "contact" | "ground_type"
    chance: float | None = None    # 0.0 - 1.0, None means always
    status: str | None = None      # status to inflict for type=="status" (e.g. "paralyzed")

@dataclass
class Ability:
    name: str
    description: str
    effects: list[AbilityEffect] = field(default_factory=list)

    def __init__(self, data: dict):
        self.name = data["name"]
        self.description = data["description"]
        self.effects = [AbilityEffect(**e) for e in data.get("effects", [])]