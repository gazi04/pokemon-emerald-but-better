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


@dataclass
class NpcSpottedPlayerEvent:
    """Fired the moment a trainer NPC sees the player in its line of sight.

    The NPC then walks up to the player on its own; the overworld freezes
    player input until the resulting dialog/battle is over.
    """

    npc_id: str


# ---------------------------------------------------------------------------
# Overworld items
# ---------------------------------------------------------------------------


@dataclass
class ItemPickedUpEvent:
    """Fired when the player presses interact facing an item on the ground.

    `key` identifies that specific pickup on that specific map, so it can be
    recorded as collected and never respawn.
    """

    key: str
    item_id: str


# ---------------------------------------------------------------------------
# Battle Phase
# ---------------------------------------------------------------------------


@dataclass
class TextMessageEvent:
    """Push a line into the active text box, from any source (system or view)."""

    message: str


@dataclass
class HpChangedEvent:
    """Fired after damage or healing is applied to a Pokémon.

    Deliberately has no production subscriber yet: it is the seam for animating
    the HP bar, which today is redrawn statelessly from the live ratio every
    frame (`battle_ui_manager.draw_hp_bar`). A consumer holding a displayed
    value and lerping it toward `new_hp` is the intended use; that work is
    blocked behind view/UI test coverage. `old_hp` exists for that tween.

    Tests are its only consumer for now — do not delete it as dead code.
    (`PokemonFaintedEvent` sat beside this one with no such plan and was
    removed; the battle flow branches on `battle_state` instead.)
    """

    target: str  # "player" or "enemy"
    old_hp: int
    new_hp: int
    max_hp: int


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
