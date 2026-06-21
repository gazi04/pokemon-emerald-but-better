from dataclasses import dataclass
from typing import Optional


@dataclass
class ItemEffect:
    type: str
    amount: Optional[int] = None
    catchRate: Optional[int] = None

    def __init__(self, effect: dict):
        self.type = effect["type"]
        self.amount = effect.get("amount")
        self.catchRate = effect.get("catchRate")


@dataclass
class ItemProfile:
    description: str
    price: int
    effects: list[ItemEffect]

    def __init__(self, item: dict, effects: list[ItemEffect]):
        self.description = item["description"]
        self.price = item["price"]
        self.effects = effects
