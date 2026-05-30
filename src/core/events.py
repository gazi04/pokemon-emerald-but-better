from dataclasses import dataclass
from src.model.pokemon import PokemonProfile


# ---------------------------------------------------------------------------
# Overworld Phase
# ---------------------------------------------------------------------------


@dataclass
class PlayerFinishedMoveEvent:
    """Fired by MovementSystem when the player lands on a new tile."""

    grid_x: float
    grid_y: float
    map_name: str


@dataclass
class BattleEncounterTriggeredEvent:
    """Fired by EncounterSystem when a wild battle should start."""

    pokemon_name: str
    pokemon_data: PokemonProfile
    pokemon_level: int


# ---------------------------------------------------------------------------
# Battle Phase
# ---------------------------------------------------------------------------


@dataclass
class BattleTextMessageEvent:
    """Fired by BattleSystem to push a line into the typewriter box."""

    message: str


@dataclass
class HpChangedEvent:
    """Fired after damage or healing is applied to a Pokémon."""

    target: str  # "player" or "enemy"
    old_hp: int
    new_hp: int
    max_hp: int


@dataclass
class PokemonFaintedEvent:
    """Fired when a Pokémon's HP reaches zero."""

    target: str  # "player" or "enemy"
    pokemon_name: str
