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

    def get_pokemon(self, name: str) -> Optional[PlayerPokemon]:
        target = name.lower()
        for pokemon in self.pokemon:
            if pokemon.name.lower() == target:
                return pokemon
        return None

    def update_hp(self, pokemon_name: str, new_hp: int):
        pokemon = self.get_pokemon(pokemon_name)
        if pokemon:
            pokemon.hp = max(new_hp, 0)

    def update_move_pp(self, pokemon_name: str, move_name: str, pp: int):
        pokemon = self.get_pokemon(pokemon_name)
        if not pokemon:
            return
        for move in pokemon.moves:
            if move.name == move_name:
                move.pp = pp

    def update_level(self, pokemon_name: str, new_level: int, exp: int, evolved_name: Optional[str] = None):
        pokemon = self.get_pokemon(pokemon_name)
        if not pokemon:
            return
        pokemon.level = new_level
        pokemon.exp = exp
        if evolved_name:
            pokemon.name = evolved_name

    def add_pokemon(self, pokemon: PlayerPokemon) -> bool:
        if len(self.pokemon) >= 6:
            return False
        self.pokemon.append(pokemon)
        self.mark_seen(pokemon.name)
        return True

    def mark_seen(self, name: str):
        if name not in self.seen:
            self.seen.append(name)


@dataclass
class PlayerState:
    profile: Optional[PlayerProfile] = None
    map_name: str = "littleroot_town"
    direction: str = "down"

    grid_x: int = 0
    grid_y: int = 0

    pixel_x: float = 0.0
    pixel_y: float = 0.0
    target_x: float = 0.0
    target_y: float = 0.0
    start_x: float = 0.0
    start_y: float = 0.0

    moving: bool = False
    move_progress: float = 0.0
    move_duration: float = 0.25
