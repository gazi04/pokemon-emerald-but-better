from dataclasses import dataclass
from typing import Optional

@dataclass
class ItemEffect:
    type: str
    amount: Optional[int] = None
    catchRate: Optional[int] = None

@dataclass
class Item:
    description: str
    price: int
    effects: list[ItemEffect]