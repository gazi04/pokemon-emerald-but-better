from dataclasses import dataclass
from typing import Optional
from src.model.player import PlayerPokemon

@dataclass
class Trainer:
    party: list[PlayerPokemon]