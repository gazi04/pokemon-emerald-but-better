import json
from pydantic import BaseModel, Field
from typing import Literal


class WindowConfig(BaseModel):
    width: int = 800
    height: int = 600
    title: str = "Pokemon Emerald But BETTER"
    fullscreen: bool = False
    resizable: bool = False


class AudioConfig(BaseModel):
    music_volume: float = 0.85
    sound_volume: float = 1.0
    battle_music_volume: float = 0.9
    mute_when_minimized: bool = True


class ControlsConfig(BaseModel):
    up: str = "UP"
    down: str = "DOWN"
    left: str = "LEFT"
    right: str = "RIGHT"
    run: str = "LSHIFT"
    interact: str = "Z"
    menu: str = "X"
    cancel: str = "ESCAPE"
    bag: str = "TAB"


class GameConfig(BaseModel):
    starting_map: str = "assets/map/littleroot_town.tmx"
    starting_tile_x: int = 15
    starting_tile_y: int = 12
    starting_money: int = 3000
    text_speed: Literal["slow", "medium", "fast"] = "medium"
    battle_style: Literal["set", "switch"] = "set"


class LoggingConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    console_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "WARNING"
    file_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "DEBUG"
    file_path: str = "logs/game.log"
    max_bytes: int = 1_000_000  # ~1 MB
    backup_count: int = 3


class Config(BaseModel):
    window: WindowConfig = Field(default_factory=WindowConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    controls: ControlsConfig = Field(default_factory=ControlsConfig)
    game: GameConfig = Field(default_factory=GameConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def load(cls):
        with open("data/config.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls.model_validate(data)
