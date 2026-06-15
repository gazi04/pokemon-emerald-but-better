from dataclasses import dataclass
from src.model.trainer import Trainer

@dataclass
class NpcProfile:
    dialog: list[str]
    action_after_dialog: str
    team: Trainer
    
    def __init__(self, data):
        self.dialog = data["dialog"]
        self.action_after_dialog = data["action_after_dialog"]
        self.team = Trainer(data.get("team", []))