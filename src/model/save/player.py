from dataclasses import dataclass, field
from src.enums.item_category import ItemCategory

MAX_PARTY = 6
BOX_CAPACITY = 30


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
    held_item: str | None
    # Persistent major status ("poison"/"burn"/… or None). Volatile states
    # (confusion, sleep counter) live only inside battle.
    status_condition: str | None = None

    @property
    def is_fainted(self) -> bool:
        return self.hp <= 0


@dataclass
class ItemStack:
    name: str
    count: int
    category: str


@dataclass
class Box:
    name: str
    pokemons: list[PlayerPokemon]


@dataclass
class PlayerSave:
    pokemon: list[PlayerPokemon]
    boxs: list[Box]
    items: dict[str, ItemStack]
    seen: list[str] = field(default_factory=list)
    money: int = 0
    npc_states: list[dict] = field(default_factory=list)
    # Keys of overworld items already picked up, so they never respawn.
    collected_items: list[str] = field(default_factory=list)

    def get_pokemon(self, name: str) -> PlayerPokemon | None:
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

    def update_status(self, pokemon_name: str, status: str | None):
        pokemon = self.get_pokemon(pokemon_name)
        if pokemon:
            pokemon.status_condition = status

    def update_level(
        self,
        pokemon_name: str,
        new_level: int,
        exp: int,
        evolved_name: str | None = None,
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

    def add_pokemon_team(self, pokemon: PlayerPokemon) -> bool:
        """Add to the party, or to storage when the party is full.

        Returns whether the pokemon was stored anywhere — callers surface that
        to the player (see BattleSystem.add_caught_pokemon).
        """
        self.mark_seen(pokemon.name)
        if len(self.pokemon) >= MAX_PARTY:
            return self.add_pokemon_box(pokemon)
        self.pokemon.append(pokemon)
        return True

    def add_pokemon_box(self, pokemon: PlayerPokemon) -> bool:
        """Store in the first box with room, opening a new box if every box is
        full. Exactly one box receives the pokemon.

        The `return` matters: this used to append to *every* non-full box, so a
        single catch was duplicated across all of them.
        """
        for box in self.boxs:
            if len(box.pokemons) >= BOX_CAPACITY:
                continue

            box.pokemons.append(pokemon)
            return True

        # Every box is full (or there are none) — open another rather than
        # dropping the pokemon on the floor.
        new_box = Box(f"Box {len(self.boxs) + 1}", [pokemon])
        self.boxs.append(new_box)
        return True

    def mark_seen(self, name: str):
        """Record a species as seen. Normalized to lowercase because the Pokédex
        matches these entries against DataLoader keys, which are lowercase ids —
        a capitalized entry renders blank while still counting toward the total.
        """
        key = name.lower()
        if key not in self.seen:
            self.seen.append(key)

    def add_item(self, item_id: str, category: str, count: int):
        item = self.items.get(item_id)

        if not item:
            self.items[item_id] = ItemStack(item_id, count, ItemCategory(category))
            return

        item.count += count

    def consume_item(self, item_id: str) -> bool:
        item = self.items.get(item_id)
        if not item:
            return False

        item.count -= 1
        if item.count <= 0:
            self.items.pop(item_id)

        return True
