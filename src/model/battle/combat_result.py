from dataclasses import dataclass, field


@dataclass
class CombatResult:
    """
    Pure data payload returned by calculate_damage().
    BattleSystem reads this to apply damage and build UI messages.
    """

    damage: int  # Final rounded damage to apply
    effectiveness: float  # Type multiplier (0, 0.5, 1, 2, 4 …)
    is_critical: bool  # Whether a critical hit occurred
    is_miss: bool  # Whether the move missed
    messages: list[str] = field(default_factory=list)  # Effectiveness/crit strings
