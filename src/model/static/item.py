from dataclasses import dataclass
from typing import Optional
from src.enums.effect_type import EffectType


@dataclass
class ItemEffect:
    type: EffectType
    amount: Optional[int] = None
    catch_rate: Optional[int] = None


@dataclass
class ItemSpecies:
    description: str
    price: int
    effects: list[ItemEffect]
