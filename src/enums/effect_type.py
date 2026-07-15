from enum import StrEnum


class EffectType(StrEnum):
    STAT = "stat"
    STATUS_CONDITION = "status condition"
    CURE_STATUS = "cure_status"
    RESTORE_PP = "restore_pp"
    PROTECT = "protect"
    HEAL = "heal"
    CATCH = "catch"
    RECOIL_TO_ATTACKER = "recoil_to_attacker"
    RECOIL_TO_SELF = "recoil_to_self"
