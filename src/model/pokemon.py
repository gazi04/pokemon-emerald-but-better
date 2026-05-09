from dataclasses import dataclass
from typing import Optional


@dataclass
class PokemonStat:
    hp: int
    attack: int
    defence: int
    special_attack: int
    special_defence: int
    speed: int

    def copy(self) -> PokemonStat:
        return PokemonStat(
            hp=self.hp,
            attack=self.attack,
            defence=self.defence,
            special_attack=self.special_attack,
            special_defence=self.special_defence,
            speed=self.speed
        )

@dataclass
class PokemonMove:
    category: str
    type: str
    power: int
    accuracy: int
    pp: int
    effects: list[PokemonMoveEffect]
    
@dataclass
class PokemonMoveEffect:
    target: str
    type: str
    stat: Optional[str] = None
    change: Optional[str] = None
    condition: Optional[str] = None
    chance: Optional[str] = None

@dataclass
class PokemonSprites:
    back: str
    front: str
    
@dataclass
class PokemonEvolution:
    to: str
    levelCap: int

@dataclass
class PokemonProfile:
    baseExp: int
    evolution: Optional[PokemonEvolution] = None
    sprites: PokemonSprites = None
    abilities: list[str] = None
    types: list[str] = None
    stats: PokemonStat = None