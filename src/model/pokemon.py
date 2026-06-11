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
            speed=self.speed,
        )


@dataclass
class PokemonMove:
    name: str
    category: str
    type: str
    power: int
    accuracy: int
    pp: int
    effects: list[PokemonMoveEffect]

    def __init__(self, name: str, move: dict, effects: list[PokemonMoveEffect]):
        self.name = name
        self.category = move["category"]
        self.type = move["type"]
        self.power = move["power"]
        self.accuracy = move["accuracy"]
        self.pp = move["pp"]
        self.effects = effects


@dataclass
class PokemonMoveEffect:
    target: str
    type: str
    stat: Optional[str] = None
    change: Optional[int] = None
    condition: Optional[str] = None
    chance: Optional[int] = None

    def __init__(self, effect: dict):
        self.target = effect["target"]
        self.type = effect["type"]
        self.stat = effect.get("stat")
        self.change = effect.get("change")
        self.condition = effect.get("condition")
        self.chance = effect.get("chance")


@dataclass
class PokemonSprites:
    back: str
    front: str


@dataclass
class PokemonEvolution:
    to: str
    levelCap: int

    def __init__(self, evolution: dict):
        self.to = evolution["to"]
        self.levelCap = evolution["level"]


@dataclass
class PokemonProfile:
    baseExp: int
    catch_rate: int = 45
    evolution: Optional[PokemonEvolution] = None
    sprites: Optional[PokemonSprites] = None
    abilities: Optional[list[str]] = None
    types: Optional[list[str]] = None
    stats: Optional[PokemonStat] = None

    def __init__(
        self,
        pokemon: dict,
        evolution: Optional[PokemonEvolution],
        sprites: PokemonSprites,
        stats: PokemonStat,
    ):
        self.baseExp = pokemon["baseExp"]
        self.catch_rate = pokemon.get("catchRate", 45)
        self.abilities = pokemon["abilities"]
        self.types = pokemon["types"]
        self.evolution = evolution
        self.sprites = sprites
        self.stats = stats
