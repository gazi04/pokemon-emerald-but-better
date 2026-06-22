from dataclasses import dataclass, field
from src.model.static.pokemon import PokemonSpecies


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
    pokemon_data: PokemonSpecies
    pokemon_level: int


# ---------------------------------------------------------------------------
# Npc
# ---------------------------------------------------------------------------


@dataclass
class NpcInteractEvent:
    """Fired when the player presses interact facing an NPC."""

    npc_id: str


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


# ---------------------------------------------------------------------------
# Navigation — used by the Game Director
# ---------------------------------------------------------------------------


@dataclass
class SwapViewEvent:
    """
    Request a full screen takeover.
    target: string key identifying the destination ("battle", "evolving")
    payload: arbitrary data the target view needs to construct itself
    """

    target: str
    payload: dict = field(default_factory=dict)


@dataclass
class CloseViewEvent:
    """
    Generic 'I am done' signal from transient views (Battle, Evolution).
    The Director will return to the cached Overworld.
    """

    pass


@dataclass
class OverlayViewEvent:
    """
    Request to stack a menu on top of the current view without swapping it.
    target: string key ("menu", "bag", "pokemon_menu")
    payload: extra data needed (e.g. battle_system reference)
    """

    target: str
    payload: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------


@dataclass
class SaveGameRequestEvent:
    """Published by MenuView when the player selects Save."""

    pass


@dataclass
class SaveCompletedEvent:
    """Published by SaveManager after the disk write finishes."""

    success: bool
