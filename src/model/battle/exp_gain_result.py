from dataclasses import dataclass, field

from src.model.static.pokemon import PokemonStat


@dataclass
class ExpGainResult:
    """Outcome of BattlePokemon.gain_exp — what changed after awarding exp."""

    leveled_up: bool
    stats_before: PokemonStat
    stats_after: PokemonStat
    evolved: bool
    evolves_to: str
    # Names of moves the pokemon reached the level to learn this gain (in order),
    # excluding moves it already knows. Empty if none.
    moves_to_learn: list[str] = field(default_factory=list)
