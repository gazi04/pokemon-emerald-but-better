from typing import Optional

from src.model.static.pokemon import PokemonEvolution


class Progression:
    """Owns a pokemon's level/exp curve and evolution check.

    Pure progression logic — no combat state, no stat recompute. The owning
    BattlePokemon reacts to a level-up (recomputing stats, healing) after
    calling add_exp; this class only tracks the numbers.
    """

    def __init__(
        self,
        level: int,
        exp: int,
        base_exp: int,
        evolution: Optional[PokemonEvolution],
    ):
        self.level = level
        self.exp = exp
        self.base_exp = base_exp
        self.evolution = evolution

    def exp_needed(self) -> int:
        return self.level**3

    def exp_yield(self) -> int:
        """Exp granted to the victor when this pokemon faints."""
        return (self.base_exp * self.level) // 7

    def exp_ratio(self) -> float:
        return self.exp / self.exp_needed()

    def add_exp(self, amount: int) -> int:
        """Add exp and level up as many times as the curve allows.

        Returns the number of levels gained (0 if none).
        """
        old_level = self.level
        self.exp += amount
        while self.exp >= self.exp_needed():
            self.exp -= self.exp_needed()
            self.level += 1
        return self.level - old_level

    def can_evolve(self) -> bool:
        return bool(self.evolution and self.evolution.levelCap <= self.level)

    @property
    def evolves_to(self) -> str:
        return self.evolution.to if self.evolution else ""
