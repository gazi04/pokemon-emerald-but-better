from src.model.pokemon import (
    PokemonProfile,
    PokemonSprites,
    PokemonStat,
    PokemonMove,
    PokemonMoveEffect,
    PokemonEvolution,
)
from src.model.item import Item, ItemEffect


class GameDataParser:
    @staticmethod
    def parse_pokemons(data: dict) -> dict[str, PokemonProfile]:
        pokemons = {}
        for name, pokemon in data.items():
            sprites = PokemonSprites(**pokemon["sprites"])
            stats = PokemonStat(**pokemon["stats"])
            evolution = PokemonEvolution(pokemon["evolution"]) if pokemon["evolution"] else None
            pokemons[name] = PokemonProfile(pokemon, evolution, sprites, stats)
        return pokemons

    @staticmethod
    def parse_moves(data: dict) -> dict[str, PokemonMove]:
        moves = {}
        for name, move in data.items():
            effects = [PokemonMoveEffect(effect) for effect in move["effects"]]
            moves[name] = PokemonMove(name, move, effects)
        return moves

    @staticmethod
    def parse_items(data: dict) -> dict[str, Item]:
        items = {}
        for name, item in data.items():
            effects = [ItemEffect(effect) for effect in item["effects"]]
            items[name] = Item(item, effects)
        return items
