from enum import StrEnum


class StatusEffect(StrEnum):
    NONE = ""
    POISON = "poison"
    PARALYSIS = "paralyzed"
    SLEEP = "sleep"
    BURN = "burn"
    FREEZE = "freeze"
    FLINCH = "flinch"
    CONFUSION = "confusion"
