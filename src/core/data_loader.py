import json
from src.model.static.pokemon import PokemonSpecies, PokemonMove
from src.model.static.item import ItemSpecies
from src.model.static.npc import NpcSpecies
from src.core.game_data_parser import GameDataParser


class DataLoader:
    def __init__(self):
        self.pokemons: dict[str, PokemonSpecies] = GameDataParser.parse_pokemons(
            self._read("data/pokemon.json")
        )
        self.moves: dict[str, PokemonMove] = GameDataParser.parse_moves(
            self._read("data/moves.json")
        )
        self.items: dict[str, ItemSpecies] = GameDataParser.parse_items(
            self._read("data/items.json")
        )
        self.npc_dialog: dict[str, NpcSpecies] = GameDataParser.parse_npc_dialog(
            self._read("data/npc_dialog.json")
        )
        # Raw dicts cached at boot — read every grass step / damage calc, so no
        # per-call file I/O (mirrors the parsed caches above).
        self.encounters: dict = self._read("data/encounters.json")
        self.types: dict = self._read("data/types.json")

    def _read(self, path: str) -> dict:
        with open(path) as f:
            return json.load(f)

    def get_pokemon(self, name: str) -> PokemonSpecies | None:
        return self.pokemons.get(name)

    def get_move(self, name: str) -> PokemonMove | None:
        return self.moves.get(name)

    def get_item(self, name: str) -> ItemSpecies | None:
        return self.items.get(name)
