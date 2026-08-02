from dataclasses import dataclass
from src.enums.item_category import ItemCategory
from src.enums.effect_type import EffectType


@dataclass
class ItemEffect:
    type: EffectType
    amount: int | None = None
    percent: float | None = None
    catch_rate: float | None = None
    stat: str | None = None
    change: int | None = None
    status: str | None = None
    full_restore: bool = False

    def __init__(self, effect: dict):
        self.type = EffectType(effect["type"])
        self.amount = effect.get("amount")
        self.percent = effect.get("percent")
        self.catch_rate = effect.get("catch_rate")
        self.stat = effect.get("stat")
        self.change = effect.get("change")
        self.status = effect.get("status")
        self.full_restore = effect.get("full_restore", False)


@dataclass
class BattleCondition:
    trigger: str
    threshold: float | None = None  # for hp_threshold
    status: str | None = None  # for on_status
    contact_only: bool = False  # for on_hit
    move_type: str | None = None  # for on_attack type filters

    def __init__(self, data: dict):
        self.trigger = data["trigger"]
        self.threshold = data.get("threshold")
        self.status = data.get("status")
        self.contact_only = data.get("contact_only", False)
        self.move_type = data.get("move_type")


@dataclass
class BattleAttributes:
    stat_multiplier: dict | None = None
    damage_multiplier: float | None = None
    restriction: str | None = None  # "lock_move"

    def __init__(self, data: dict):
        self.stat_multiplier = data.get("stat_multiplier")
        self.damage_multiplier = data.get("damage_multiplier")
        self.restriction = data.get("restriction")


@dataclass
class ItemSpecies:
    name: str  # display name, set by the parser from the data key
    description: str
    price: int
    category: str  # "medicine" | "pokeball" | "berry" | "held_item"
    holdable: bool
    effects: list[ItemEffect]
    battle_condition: BattleCondition | None
    battle_attributes: BattleAttributes | None

    def __init__(self, item: dict):
        self.name = item.get("name", "")
        self.description = item["description"]
        self.price = item["price"]
        self.category = ItemCategory(item["category"])
        self.holdable = item["holdable"]
        self.effects = [ItemEffect(e) for e in item.get("effects", [])]
        self.battle_condition = (
            BattleCondition(item["battle_condition"])
            if item.get("battle_condition")
            else None
        )
        self.battle_attributes = (
            BattleAttributes(item["battle_attributes"])
            if item.get("battle_attributes")
            else None
        )
