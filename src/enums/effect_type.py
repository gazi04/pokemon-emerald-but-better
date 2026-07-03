from enum import StrEnum


class EffectType(StrEnum):
    STAT = "stat"
    STATUS_CONDITION = "status condition"
    PROTECT = "protect"
    HEAL = "heal"
    CATCH = "catch"
