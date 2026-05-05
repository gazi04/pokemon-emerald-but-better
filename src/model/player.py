from dataclasses import dataclass
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