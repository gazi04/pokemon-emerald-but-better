"""
Manages NPC interaction state (has_fought, has_talked, etc.).
Each NPC can have multiple states and dialogs for each state.
"""
from src.model.npc import NPCState

class NPCManager:
    """
    Tracks interaction state for all NPCs.
    Single responsibility: manage NPC state only.
    """

    def __init__(self):
        self._npc_states: dict[str, NPCState] = {}

    def get_state(self, npc_id: str) -> NPCState:
        """Get or create state for an NPC."""
        if npc_id not in self._npc_states:
            self._npc_states[npc_id] = NPCState(npc_id)
        return self._npc_states[npc_id]

    def mark_talked(self, npc_id: str):
        """Mark NPC as talked to."""
        state = self.get_state(npc_id)
        state.has_talked = True

    def mark_fought(self, npc_id: str):
        """Mark NPC as fought (battle started)."""
        state = self.get_state(npc_id)
        state.has_fought = True

    def mark_defeated(self, npc_id: str):
        """Mark NPC as defeated in battle."""
        state = self.get_state(npc_id)
        state.defeated = True

    def can_fight(self, npc_id: str) -> bool:
        """Check if NPC can be fought (not already defeated)."""
        state = self.get_state(npc_id)
        return not state.defeated

    def set_flag(self, npc_id: str, flag_name: str, value: bool):
        """Set a custom state flag (e.g., 'gave_item', 'completed_quest')."""
        state = self.get_state(npc_id)
        state.custom_flags[flag_name] = value

    def get_flag(self, npc_id: str, flag_name: str, default: bool = False) -> bool:
        """Get a custom state flag."""
        state = self.get_state(npc_id)
        return state.custom_flags.get(flag_name, default)

    def load_from_dict(self, data: list[dict]):
        """Load NPC states from save data."""
        self._npc_states.clear()
        for npc_data in data:
            state = NPCState.from_dict(npc_data)
            self._npc_states[state.npc_id] = state

    def save_to_dict(self) -> list[dict]:
        """Save NPC states to dict (for JSON serialization)."""
        return [state.to_dict() for state in self._npc_states.values()]
