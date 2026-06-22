from dataclasses import dataclass, field
from src.model.static.trainer import Trainer

DEFAULT_STATE = "default"


@dataclass
class NpcSpecies:
    name: str
    dialogs: dict[str, list[str]]  # state -> lines, e.g. "first_encounter", "after_battle"
    action_after_dialog: str
    team: Trainer

    def get_dialog(self, state: str = DEFAULT_STATE) -> list[str]:
        """
        Return the lines for a given state, falling back gracefully:
        requested state -> default -> first_encounter -> any -> placeholder.
        """
        if state in self.dialogs:
            return self.dialogs[state]
        if DEFAULT_STATE in self.dialogs:
            return self.dialogs[DEFAULT_STATE]
        if "first_encounter" in self.dialogs:
            return self.dialogs["first_encounter"]
        for lines in self.dialogs.values():
            return lines
        return ["..."]

    def has_state(self, state: str) -> bool:
        return state in self.dialogs


@dataclass
class NPCState:
    """Tracks the interaction history of a single NPC."""

    npc_id: str
    has_talked: bool = False
    has_fought: bool = False
    defeated: bool = False
    custom_flags: dict = field(default_factory=dict)  # For game-specific states

    def to_dict(self) -> dict:
        """Serialize to JSON."""
        return {
            "npc_id": self.npc_id,
            "has_talked": self.has_talked,
            "has_fought": self.has_fought,
            "defeated": self.defeated,
            "custom_flags": self.custom_flags,
        }

    @staticmethod
    def from_dict(data: dict) -> "NPCState":
        """Deserialize from JSON."""
        return NPCState(
            npc_id=data.get("npc_id", ""),
            has_talked=data.get("has_talked", False),
            has_fought=data.get("has_fought", False),
            defeated=data.get("defeated", False),
            custom_flags=data.get("custom_flags", {}),
        )
