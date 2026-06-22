from dataclasses import dataclass
from typing import Optional


@dataclass
class ItemEffect:
    type: str
    amount: Optional[int] = None
    catch_rate: Optional[int] = None


@dataclass
class ItemSpecies:
    description: str
    price: int
    effects: list[ItemEffect]
