import json
import os
import shutil
from src.model.save.player import PlayerSave
from src.core.player_serializer import PlayerSerializer
from src.core.logger import get_logger

SAVE_PATH = "data/save.json"
SAVE_TMP_PATH = "data/save.tmp.json"
SAVE_BAK_PATH = "data/save.bak.json"
DEFAULT_PATH = "data/player.json"

log = get_logger(__name__)


class SaveManager:
    def __init__(self):
        self.player, self.saved_position = self._load()

    def _load(self) -> tuple[PlayerSave, dict | None]:
        """Return the loaded player and its saved position, or raise.

        Total by construction: every path either returns a PlayerSave or raises,
        which is what lets `self.player` be non-Optional for the rest of the app.
        """
        # Try the live save first, then the backup, then the shipped default.
        # A corrupt/partial save (crash mid-write, bad edit, schema drift) must
        # never brick startup — fall back instead of letting json/KeyError escape.
        candidates = [p for p in (SAVE_PATH, SAVE_BAK_PATH) if os.path.exists(p)]
        candidates.append(DEFAULT_PATH)

        last_error: Exception | None = None
        for path in candidates:
            try:
                with open(path) as f:
                    data = json.load(f)
                player = PlayerSerializer.deserialize(data)
                if path != SAVE_PATH:
                    log.warning("Loaded save from fallback '%s'", path)
                return player, data.get("position")
            except (OSError, json.JSONDecodeError, KeyError, TypeError) as e:
                last_error = e
                log.warning("Failed to load save '%s': %s", path, e)

        # Even the shipped default failed — unrecoverable install.
        raise RuntimeError(
            f"Could not load any save (tried {candidates})"
        ) from last_error

    def flush_save(self, player_state) -> bool:
        try:
            data = PlayerSerializer.serialize(self.player, player_state)

            with open(SAVE_TMP_PATH, "w") as f:
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())  # force tmp contents to disk before the rename

            if os.path.exists(SAVE_PATH):
                try:
                    shutil.copy2(SAVE_PATH, SAVE_BAK_PATH)
                except Exception as e:
                    # Backup is best-effort — never let it block promoting a
                    # good, already-fsynced save.
                    log.warning("Failed to back up save '%s': %s", SAVE_PATH, e)

            os.replace(SAVE_TMP_PATH, SAVE_PATH)
            self.saved_position = data.get("position")
            return True
        except Exception:
            log.exception("Save failed")
            return False
