import json
import os
import shutil
from typing import Optional
from src.model.save.player import PlayerSave
from src.core.player_serializer import PlayerSerializer

SAVE_PATH = "data/save.json"
SAVE_TMP_PATH = "data/save.tmp.json"
SAVE_BAK_PATH = "data/save.bak.json"
DEFAULT_PATH = "data/player.json"


class SaveManager:
    def __init__(self):
        self.saved_position: Optional[dict] = None
        self.player: Optional[PlayerSave] = None
        self.load()

    def load(self):
        path = SAVE_PATH if os.path.exists(SAVE_PATH) else DEFAULT_PATH
        with open(path, "r") as f:
            data = json.load(f)

        self.player = PlayerSerializer.deserialize(data)

        if "position" in data:
            self.saved_position = data["position"]

    def flush_save(self, player_state) -> bool:
        try:
            position = {
                "map_name": player_state.map_name,
                "direction": player_state.direction,
                "pixel_x": player_state.pixel_x,
                "pixel_y": player_state.pixel_y,
            }
            data = PlayerSerializer.serialize(self.player, position)

            with open(SAVE_TMP_PATH, "w") as f:
                json.dump(data, f, indent=4)

            if os.path.exists(SAVE_PATH):
                shutil.copy2(SAVE_PATH, SAVE_BAK_PATH)

            os.replace(SAVE_TMP_PATH, SAVE_PATH)
            self.saved_position = data["position"]
            return True
        except Exception:
            return False
