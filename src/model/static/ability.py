from dataclasses import dataclass, field
from src.enums.stat import Stat
from src.enums.status_effect import StatusEffect
from src.enums.weather import Weather
from src.enums.ability import AbilityTypes, AbilityCondition, AbilityTrigger

@dataclass
class AbilityEffect:
    trigger: AbilityTrigger  
    type: AbilityTypes  
    target: str | None = None  # "self" | "enemy"
    move_type: str | None = None  # only apply if the move matches this type
    stat: Stat | None = None
    change: int | None = None
    condition: AbilityCondition | None = None  
    chance: float | None = None  # 0.0 - 1.0, None means always
    status: StatusEffect | None = None  
    weather: Weather | None = None  
    
    def __init__(self, data: dict):
        self.trigger = data["trigger"]
        self.type = data["type"]
        self.target = data.get("target")
        self.move_type = data.get("move_type")
        self.stat = data.get("stat")
        self.change = data.get("change")
        self.condition = data.get("condition")
        self.chance = data.get("chance")
        self.status = data.get("status")
        self.weather = data.get("weather")

@dataclass
class Ability:
    name: str
    description: str
    effects: list[AbilityEffect] = field(default_factory=list)

    def __init__(self, data: dict):
        self.name = data["name"]
        self.description = data["description"]
        self.effects = [AbilityEffect(e) for e in data.get("effects", [])]
