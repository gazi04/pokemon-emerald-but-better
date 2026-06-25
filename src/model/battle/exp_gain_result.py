from dataclasses import dataclass

from src.model.static.pokemon import PokemonStat


@dataclass
class ExpGainResult:
    """Outcome of BattlePokemon.gain_exp — what changed after awarding exp."""

    leveled_up: bool
    stats_before: PokemonStat
    stats_after: PokemonStat
    evolved: bool
    evolves_to: str
