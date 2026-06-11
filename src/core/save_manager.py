import json
from typing import Optional
from src.model.player import (
    PlayerProfile,
    Item,
    PlayerPokemonMove,
    PlayerPokemon,
)

class SaveManager:
    def __init__(self):
        self.loadData()

    def loadData(self):
        with open("data/player.json", "r") as f:
            data = json.load(f)

        self.player = self.parsePlayer(data)

    def parsePlayer(self, data) -> PlayerProfile:
        pokemons = []
        items = []
        pokeballs = []

        for pokemon in data["pokemon"]:
            moves = []

            for move in pokemon["moves"]:
                moves.append(PlayerPokemonMove(name=move["name"], pp=move["pp"]))

            pokemons.append(
                PlayerPokemon(
                    name=pokemon["name"],
                    hp=pokemon["hp"],
                    level=pokemon["level"],
                    exp=pokemon["exp"],
                    moves=moves,
                )
            )

        for item in data["items"]:
            items.append(Item(item["name"], item["count"]))

        for pokeball in data["pokeballs"]:
            pokeballs.append(Item(pokeball["name"], pokeball["count"]))

        seen = data.get("seen", [])
        return PlayerProfile(pokemon=pokemons, items=items, pokeballs=pokeballs, seen=seen)

    def addPokemon(self, name: str, hp: int, level: int, moves: list[PlayerPokemonMove]):
        if len(self.player.pokemon) >= 6:
            return False
        
        self.player.pokemon.append(PlayerPokemon(
            name=name,
            hp=hp,
            level=level,
            exp=0,
            moves=moves
        ))
        
    def getPokemon(self, pokemonId: str) -> Optional[PlayerPokemon]:
        if not self.player:
            return None
        
        for pokemon in self.player.pokemon:
            if pokemon.name == pokemonId:
                return pokemon

        return None

    def updateHp(self, pokemonId, newHp):
        pokemon = self.getPokemon(pokemonId)
        print(newHp)

        if pokemon:
            pokemon.hp = max(newHp, 0)

    def updateMove(self, pokemonId, move, pp):
        pokemon = self.getPokemon(pokemonId)

        if not pokemon:
            return

        for move in pokemon.moves:
            if move.name == move:
                move.pp = pp

    def addPokemon(self, pokemon: PlayerPokemon):
        """Adds a newly caught Pokémon to the player's party (max 6)."""
        if len(self.player.pokemon) < 6:
            self.player.pokemon.append(pokemon)
            # Also mark it as seen
            self.markSeen(pokemon.name)

    def markSeen(self, name: str):
        """Records a Pokémon as seen in the Pokédex."""
        if name not in self.player.seen:
            self.player.seen.append(name)

    def updateLevel(self, pokemonId, newLevel, currentExp, evolvedName=None):
        pokemon = self.getPokemon(pokemonId)

        if not pokemon:
            return

        pokemon.level = newLevel
        pokemon.exp = currentExp

        if evolvedName:
            pokemon.name = evolvedName

    def flushToDisk(self):
        if not self.player:
            return

        data = self.deparsePlayer()

        with open("data/player.json", "w") as f:
            json.dump(data, f, indent=4)

    def deparsePlayer(self):
        items = []
        pokeballs = []
        pokemons = []

        if not self.player:
            return {"pokemon": [], "items": [], "pokeballs": []}

        for item in self.player.items:
            items.append({"name": item.name, "count": item.count})

        for pokeball in self.player.pokeballs:
            pokeballs.append({"name": pokeball.name, "count": pokeball.count})

        for pokemon in self.player.pokemon:
            moves = []

            for move in pokemon.moves:
                moves.append({"name": move.name, "pp": move.pp})

            pokemons.append(
                {
                    "name": pokemon.name,
                    "hp": pokemon.hp,
                    "level": pokemon.level,
                    "exp": pokemon.exp,
                    "moves": moves,
                }
            )

        return {
            "pokemons": pokemons,
            "items": items,
            "pokeballs": pokeballs,
            "seen": list(self.player.seen),
        }
