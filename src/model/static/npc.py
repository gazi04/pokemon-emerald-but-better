from dataclasses import dataclass
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
