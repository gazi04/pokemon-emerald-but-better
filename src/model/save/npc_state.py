from dataclasses import dataclass, field


@dataclass
class NPCState:
    """Tracks the interaction history of a single NPC."""

    npc_id: str
    has_talked: bool = False
    has_fought: bool = False
    defeated: bool = False
    custom_flags: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "npc_id": self.npc_id,
            "has_talked": self.has_talked,
            "has_fought": self.has_fought,
            "defeated": self.defeated,
            "custom_flags": self.custom_flags,
        }

    @staticmethod
    def from_dict(data: dict) -> "NPCState":
        return NPCState(
            npc_id=data.get("npc_id", ""),
            has_talked=data.get("has_talked", False),
            has_fought=data.get("has_fought", False),
            defeated=data.get("defeated", False),
            custom_flags=data.get("custom_flags", {}),
        )
