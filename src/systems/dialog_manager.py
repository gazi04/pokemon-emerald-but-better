"""
Manages NPC dialogs and selects appropriate dialog based on NPC state.
Single responsibility: dialog retrieval and selection logic.
"""

import json
from src.systems.npc_manager import NPCManager
from src.core.logger import get_logger

log = get_logger(__name__)


class DialogManager:
    """
    Loads dialogs from JSON and returns appropriate dialog based on NPC state.
    Dialog JSON structure:
    {
        "npc_id": {
            "first_encounter": ["Hello!", "Nice to meet you"],
            "after_defeat": ["You beat me..."],
            "default": ["How can I help?"]
        }
    }
    """

    def __init__(
        self, npc_manager: NPCManager, dialog_path: str = "data/npc_dialog.json"
    ):
        self.npc_manager = npc_manager
        self.dialogs: dict = {}
        self._load_dialogs(dialog_path)

    def _load_dialogs(self, path: str):
        """Load dialog data from JSON file."""
        try:
            with open(path) as f:
                self.dialogs = json.load(f)
        except FileNotFoundError:
            log.warning("Dialog file not found at %s", path)
            self.dialogs = {}

    def get_dialog_lines(self, npc_id: str) -> list[str]:
        """
        Get dialog lines for NPC based on their current state.
        Returns appropriate dialog based on interaction history.
        """
        if npc_id not in self.dialogs:
            return ["..."]  # Fallback if NPC has no dialog

        npc_dialogs = self.dialogs[npc_id]
        npc_state = self.npc_manager.get_state(npc_id)

        # Priority: state-specific dialog > default
        # Check specific states in order
        if npc_state.defeated and "after_defeat" in npc_dialogs:
            return npc_dialogs["after_defeat"]

        if npc_state.has_fought and "after_fight" in npc_dialogs:
            return npc_dialogs["after_fight"]

        if npc_state.has_talked and "revisit" in npc_dialogs:
            return npc_dialogs["revisit"]

        if not npc_state.has_talked and "first_encounter" in npc_dialogs:
            return npc_dialogs["first_encounter"]

        # Fallback to default
        if "default" in npc_dialogs:
            return npc_dialogs["default"]

        # Last resort: return first available dialog
        for lines in npc_dialogs.values():
            if isinstance(lines, list) and lines:
                return lines

        return ["..."]

    def get_dialog_type(self, npc_id: str) -> str:
        """
        Determine which dialog type is being used.
        Useful for logic that depends on the state (e.g., is this a battle NPC?).
        """
        if npc_id not in self.dialogs:
            return "none"

        npc_state = self.npc_manager.get_state(npc_id)

        if npc_state.defeated:
            return "after_defeat"
        if npc_state.has_fought:
            return "after_fight"
        if npc_state.has_talked:
            return "revisit"
        if not npc_state.has_talked:
            return "first_encounter"
        return "default"

    def has_battle_dialog(self, npc_id: str) -> bool:
        """Check if this NPC has battle-related dialogs."""
        if npc_id not in self.dialogs:
            return False
        npc_dialogs = self.dialogs[npc_id]
        return "after_fight" in npc_dialogs or "after_defeat" in npc_dialogs
