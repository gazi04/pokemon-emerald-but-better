import json
import os
import shutil
from typing import Optional
from src.model.player import (
    PlayerProfile,
    Item,
    PlayerPokemonMove,
    PlayerPokemon,
)

SAVE_PATH = "data/save.json"
SAVE_TMP_PATH = "data/save.tmp.json"
SAVE_BAK_PATH = "data/save.bak.json"
DEFAULT_PATH = "data/player.json"


class SaveManager:
    def __init__(self):
        self.saved_position: Optional[dict] = None
        self.loadData()

    def loadData(self):
        path = SAVE_PATH if os.path.exists(SAVE_PATH) else DEFAULT_PATH
        with open(path, "r") as f:
            data = json.load(f)

        self.player = self.parsePlayer(data)

        if "position" in data:
            self.saved_position = data["position"]

    def parsePlayer(self, data) -> PlayerProfile:
        pokemons = []
        items = []
        pokeballs = []

        for pokemon in data["pokemons"]:
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

        return PlayerProfile(pokemon=pokemons, items=items, pokeballs=pokeballs)

    def getPokemon(self, pokemonId: str) -> Optional[PlayerPokemon]:
        if not self.player:
            return None

        target = pokemonId.lower()
        for pokemon in self.player.pokemon:
            if pokemon.name.lower() == target:
                return pokemon

        return None

    def updateHp(self, pokemonId, newHp):
        pokemon = self.getPokemon(pokemonId)

        if pokemon:
            pokemon.hp = max(newHp, 0)

    def updateMove(self, pokemonId, moveName, pp):
        pokemon = self.getPokemon(pokemonId)

        if not pokemon:
            return

        for move in pokemon.moves:
            if move.name == moveName:
                move.pp = pp

    def updateLevel(self, pokemonId, newLevel, currentExp, evolvedName=None):
        pokemon = self.getPokemon(pokemonId)

        if not pokemon:
            return

        pokemon.level = newLevel
        pokemon.exp = currentExp

        if evolvedName:
            pokemon.name = evolvedName

    def compile_save_state(self, player_state) -> dict:
        data = self.deparsePlayer()
        data["position"] = {
            "map_name": player_state.map_name,
            "direction": player_state.direction,
            "pixel_x": player_state.pixel_x,
            "pixel_y": player_state.pixel_y,
        }
        return data

    def flush_save(self, player_state) -> bool:
        try:
            data = self.compile_save_state(player_state)

            with open(SAVE_TMP_PATH, "w") as f:
                json.dump(data, f, indent=4)

            if os.path.exists(SAVE_PATH):
                shutil.copy2(SAVE_PATH, SAVE_BAK_PATH)

            os.replace(SAVE_TMP_PATH, SAVE_PATH)
            self.saved_position = data["position"]
            return True
        except Exception:
            return False

    def deparsePlayer(self):
        items = []
        pokeballs = []
        pokemons = []

        if not self.player:
            return {"pokemons": [], "items": [], "pokeballs": []}

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

        return {"pokemons": pokemons, "items": items, "pokeballs": pokeballs}

    # Legacy alias kept for compatibility
    def flushToDisk(self):
        if not self.player:
            return
        data = self.deparsePlayer()
        with open(DEFAULT_PATH, "w") as f:
            json.dump(data, f, indent=4)
