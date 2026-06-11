from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlayerPokemonMove:
    name: str
    pp: int


@dataclass
class PlayerPokemon:
    name: str
    hp: int
    level: int
    exp: int
    moves: list[PlayerPokemonMove]


@dataclass
class Item:
    name: str
    count: int


@dataclass
class Pokeball:
    name: str
    count: int


@dataclass
class PlayerProfile:
    pokemon: list[PlayerPokemon]
    items: list[Item]
    pokeballs: list[Pokeball]
    seen: list[str] = field(default_factory=list)
    money: int = 0
    money: int = 0


@dataclass
class PlayerState:
    profile: Optional[PlayerProfile] = None
    map_name: str = "littleroot_town"
    direction: str = "down"

    # Logic coordinates
    grid_x: int = 0
    grid_y: int = 0

    # Pixel coordinates for view handling
    pixel_x: float = 0.0
    pixel_y: float = 0.0
    target_x: float = 0.0
    target_y: float = 0.0
    start_x: float = 0.0
    start_y: float = 0.0

    moving: bool = False
    move_progress: float = 0.0
    move_duration: float = 0.25
