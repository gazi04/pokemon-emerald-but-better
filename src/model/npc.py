from dataclasses import dataclass

@dataclass
class NpcDialog:
    dialog: list[str]
    action_after_dialog: str
    
    def __init__(self, data):
        self.dialog = data["dialog"]
        self.action_after_dialog = data["action_after_dialog"]