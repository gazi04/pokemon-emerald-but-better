from enum import StrEnum


class AbilityTypes(StrEnum):
    STATUS = "status"
    SPEED = "speed"
    IMMUNITY = "immunity"
    IMMUNITY_STAT = "immunity_stat"
    IMMUNITY_MOVE_EFFECTS = "immunity_move_effects"
    IMMUNITY_STATUS_EFFECT = "immunity_status_effect"
    WEATHER = "weather"
    STAT_CHANGE = "stat_change"
    HEAL = "heal"
    DAMAGE_BOOST = "damage_boost"
    CURE_STATUS = "cure_status"
    ABSORB = "absorb"
    PASSES_STATUS_EFFECT = "passes_status_effect"


class AbilityTrigger(StrEnum):
    ON_HIT = "on_hit"
    ON_ATTACK = "on_attack"
    ON_SWITCH_IN = "on_switch_in"
    ON_TURN_END = "on_turn_end"
    WEATHER = "weather"
    ON_STAT_CHANGE = "on_stat_change"


class AbilityCondition(StrEnum):
    HAS_STATUS_EFFECT = "has_status_effect"
    CONTACT = "contact"
    LOW_HP = "low_hp"
    GROUND_TYPE = "ground_type"
