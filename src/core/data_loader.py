import json
from src.model.pokemon import PokemonProfile, PokemonMove
from src.model.item import Item
from src.model.npc import NpcProfile
from src.core.game_data_parser import GameDataParser


class DataLoader:
    def __init__(self):
        self.pokemons: dict[str, PokemonProfile] = GameDataParser.parse_pokemons(self._read("data/pokemon.json"))
        self.moves: dict[str, PokemonMove] = GameDataParser.parse_moves(self._read("data/moves.json"))
        self.items: dict[str, Item] = GameDataParser.parse_items(self._read("data/items.json"))
        self.npc_dialog: dict[str, NpcProfile] = GameDataParser.parse_npc_dialog(self._read("data/npc_dialog.json"))
        
        print(self.npc_dialog)

    def _read(self, path: str) -> dict:
        with open(path) as f:
            return json.load(f)

    def get_pokemon(self, name: str) -> PokemonProfile | None:
        return self.pokemons.get(name)

    def get_move(self, name: str) -> PokemonMove | None:
        return self.moves.get(name)

    def get_item(self, name: str) -> Item | None:
        return self.items.get(name)
