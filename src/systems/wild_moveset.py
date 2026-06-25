"""Pick a wild Pokémon's moves from its species learnset.

Pure data in, pure data out — no arcade, mirrors combat_calculator. The wild
knows the last MAX_MOVES it would have learned by its level; species with no
learnset fall back to Tackle so a wild is never moveless.
"""

from src.core.data_loader import DataLoader
from src.model.static.pokemon import PokemonSpecies
from src.model.save.player import PlayerPokemonMove

MAX_MOVES = 4
DEFAULT_WILD_MOVE = ("tackle", 35)


def select_wild_moves(
    species: PokemonSpecies, level: int, data_loader: DataLoader
) -> list[PlayerPokemonMove]:
    learned = sorted(
        (m for m in species.learnset if m.level <= level),
        key=lambda m: m.level,
    )[-MAX_MOVES:]

    moves = []
    for entry in learned:
        move = data_loader.get_move(entry.move)
        if move:
            moves.append(PlayerPokemonMove(entry.move, move.pp))

    return moves or [PlayerPokemonMove(*DEFAULT_WILD_MOVE)]
