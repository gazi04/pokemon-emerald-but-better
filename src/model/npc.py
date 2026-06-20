from dataclasses import dataclass, field
from src.model.trainer import Trainer

DEFAULT_STATE = "default"

# Keys that are NOT dialog states — everything else is treated as a state.
_RESERVED_KEYS = {"name", "action_after_dialog", "team"}


@dataclass
class NpcProfile:
    name: str
    dialogs: dict[
        str, list[str]
    ]  # state -> lines, e.g. "first_encounter", "after_battle"
    action_after_dialog: str
    team: Trainer

    def __init__(self, data: dict):
        self.name = data.get("name", "")
        self.dialogs = self._parse_dialogs(data["dialog"])
        self.action_after_dialog = data.get("action_after_dialog", "end")
        self.team = Trainer(data.get("team", []))

    def _parse_dialogs(self, data: dict) -> dict[str, list[str]]:
        """
        Every list-valued key (except reserved ones) is a dialog state.
        The legacy single "dialog" key is mapped to the default state.
        """
        dialogs: dict[str, list[str]] = {}

        for key, value in data.items():
            if key in _RESERVED_KEYS or not isinstance(value, list):
                continue
            state = DEFAULT_STATE if key == "dialog" else key
            dialogs[state] = value

        return dialogs

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
