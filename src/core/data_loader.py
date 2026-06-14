import json
from src.model.pokemon import (
    PokemonProfile,
    PokemonSprites,
    PokemonStat,
    PokemonMove,
    PokemonMoveEffect,
    PokemonEvolution,
)
from src.model.item import Item, ItemEffect
from src.model.npc import NpcDialog


class DataLoader:
    def __init__(self):
        self.pokemons: dict[str, PokemonProfile] = {}
        self.moves: dict[str, PokemonMove] = {}
        self.items: dict[str, Item] = {}
        self.npc_dialog: dict[str, NpcDialog] = {}

        self._loadPokemons()
        self._loadMoves()
        self._loadItems()
        self._load_npc_dialog()

    def getMove(self, name) -> PokemonMove | None:
        return self.moves.get(name)

    def getPokemon(self, name) -> PokemonProfile | None:
        return self.pokemons.get(name)

    def getItem(self, name) -> Item | None:
        return self.items.get(name)

    def _loadPokemons(self):
        with open("data/pokemon.json", "r") as f:
            data = json.load(f)

        for name, pokemon in data.items():
            sprites = PokemonSprites(**pokemon["sprites"])
            stats = PokemonStat(**pokemon["stats"])
            evolution = (
                PokemonEvolution(pokemon["evolution"]) if pokemon["evolution"] else None
            )

            self.pokemons[name] = PokemonProfile(pokemon, evolution, sprites, stats)

    def _loadMoves(self):
        with open("data/moves.json", "r") as f:
            data = json.load(f)

        for name, move in data.items():
            effects = [PokemonMoveEffect(effect) for effect in move["effects"]]

            self.moves[name] = PokemonMove(name, move, effects)

    def _loadItems(self):
        with open("data/items.json", "r") as f:
            data = json.load(f)

        for name, item in data.items():
            effects = [ItemEffect(effect) for effect in item["effects"]]

            self.items[name] = Item(item, effects)
            
    def _load_npc_dialog(self):
        with open("data/npc_dialog.json", "r") as f:
            data = json.load(f)
            
        for name, item in data.items():
            self.npc_dialog[name] = NpcDialog(item["dialog"], item["action_after_dialog"])
