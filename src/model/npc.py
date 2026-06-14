from dataclasses import dataclass

@dataclass
class NpcDialog:
    dialog: list[str]
    action_after_dialog: str