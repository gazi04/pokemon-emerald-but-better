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
    ability: str
    moves: list[PlayerPokemonMove]

    @property
    def is_fainted(self) -> bool:
        return self.hp <= 0


@dataclass
class ItemStack:
    name: str
    count: int


@dataclass
class PlayerSave:
    pokemon: list[PlayerPokemon]
    items: list[ItemStack]
    pokeballs: list[ItemStack]
    seen: list[str] = field(default_factory=list)
    money: int = 0
    npc_states: list[dict] = field(default_factory=list)

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

    def update_level(
        self,
        pokemon_name: str,
        new_level: int,
        exp: int,
        evolved_name: Optional[str] = None,
    ):
        pokemon = self.get_pokemon(pokemon_name)
        if not pokemon:
            return
        pokemon.level = new_level
        pokemon.exp = exp
        if evolved_name:
            pokemon.name = evolved_name

    def learn_move(self, pokemon_name: str, move: PlayerPokemonMove):
        pokemon = self.get_pokemon(pokemon_name)
        if not pokemon:
            return
        
        if len(pokemon.moves) == 4:
            return
        
        pokemon.moves.append(move)
        
    def replace_move(self, pokemon_name: str, move: PlayerPokemonMove, index: int):
        pokemon = self.get_pokemon(pokemon_name)
        if not pokemon:
            return
        
        if len(pokemon.moves) < 4:
            return
        
        pokemon.moves[index] = move

    def add_pokemon(self, pokemon: PlayerPokemon) -> bool:
        if len(self.pokemon) >= 6:
            return False
        self.pokemon.append(pokemon)
        self.mark_seen(pokemon.name)
        return True

    def mark_seen(self, name: str):
        if name not in self.seen:
            self.seen.append(name)

    def consume_item(self, name: str) -> bool:
        return self._consume(self.items, name)

    def consume_pokeball(self, name: str) -> bool:
        return self._consume(self.pokeballs, name)

    @staticmethod
    def _consume(stacks: "list[ItemStack]", name: str) -> bool:
        for i, stack in enumerate(stacks):
            if stack.name == name:
                stack.count -= 1
                if stack.count <= 0:
                    stacks.pop(i)
                return True
        return False
