from dataclasses import dataclass
from src.model.player import PlayerPokemon

@dataclass
class Trainer:
    party: list[PlayerPokemon]