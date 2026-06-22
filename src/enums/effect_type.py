from enum import StrEnum


class EffectType(StrEnum):
    STAT = "stat"
    STATUS_CONDITION = "status condition"
    HEAL = "heal"
    CATCH = "catch"
