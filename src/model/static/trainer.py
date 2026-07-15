from dataclasses import dataclass, field


@dataclass
class TrainerPokemonMove:
    name: str
    pp: int


@dataclass
class TrainerPokemon:
    """A trainer's roster entry — a template/spec, not a save record.

    Lives in the static layer; unlike PlayerPokemon it carries no live
    save state (current hp, accrued exp). Only what a battle needs to
    instantiate the foe: name, level, and its moves.
    """

    name: str
    level: int
    ability: str
    held_item: str | None
    moves: list[TrainerPokemonMove]


@dataclass
class Trainer:
    party: list[TrainerPokemon] = field(default_factory=list)

    def __init__(self, data):
        self.party = []

        for pokemon in data:
            moves = [
                TrainerPokemonMove(move["name"], move["pp"])
                for move in pokemon["moves"]
            ]
            self.party.append(
                TrainerPokemon(
                    pokemon["name"],
                    pokemon["level"],
                    pokemon["ability"],
                    pokemon["held_item"],
                    moves,
                )
            )
