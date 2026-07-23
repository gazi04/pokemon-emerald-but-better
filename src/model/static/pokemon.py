from dataclasses import dataclass, field
from typing import Optional

from src.enums.stat import Stat
from src.enums.status_effect import StatusEffect
from src.enums.effect_type import EffectType


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

    @staticmethod
    def scaled(base: int, level: int, is_hp: bool = False) -> int:
        """The one canonical leveled-stat formula. HP gets the extra +level term."""
        value = ((2 * base * level) // 100) + 5
        return value + level if is_hp else value

    @staticmethod
    def max_hp(base_hp: int, level: int) -> int:
        return PokemonStat.scaled(base_hp, level, is_hp=True)

    def at_level(self, level: int) -> PokemonStat:
        """Treat self as a species base stat; return the leveled stat block."""
        return PokemonStat(
            hp=PokemonStat.scaled(self.hp, level, is_hp=True),
            attack=PokemonStat.scaled(self.attack, level),
            defence=PokemonStat.scaled(self.defence, level),
            special_attack=PokemonStat.scaled(self.special_attack, level),
            special_defence=PokemonStat.scaled(self.special_defence, level),
            speed=PokemonStat.scaled(self.speed, level),
        )


@dataclass
class PokemonMoveEffect:
    target: str
    type: EffectType
    stat: Optional[Stat] = None
    change: Optional[int] = None
    condition: Optional[StatusEffect] = None
    chance: Optional[int] = None


@dataclass
class PokemonMove:
    name: str
    category: str
    type: str
    # Status moves have no power, and a few moves never miss: both are null in
    # moves.json, and every consumer already treats them as optional.
    power: int | None
    accuracy: int | None
    pp: int
    priority: int
    crit: int
    multi_hit: list[int] | None
    condition: str | None
    effects: list[PokemonMoveEffect]


@dataclass
class SpritePaths:
    back: str
    front: str


@dataclass
class PokemonEvolution:
    to: str
    levelCap: int


@dataclass
class LearnsetMove:
    move: str
    level: int


@dataclass
class PokemonSpecies:
    baseExp: int
    catch_rate: int
    abilities: list[str]
    types: list[str]
    evolution: Optional[PokemonEvolution]
    sprites: SpritePaths
    stats: PokemonStat
    learnset: list[LearnsetMove] = field(default_factory=list)
