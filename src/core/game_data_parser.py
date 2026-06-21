from src.model.pokemon import (
    PokemonProfile,
    PokemonSprites,
    PokemonStat,
    PokemonMove,
    PokemonMoveEffect,
    PokemonEvolution,
)
from src.model.item import ItemProfile, ItemEffect
from src.model.npc import NpcProfile


class GameDataParser:
    @staticmethod
    def parse_pokemons(data: dict) -> dict[str, PokemonProfile]:
        pokemons = {}
        for name, raw in data.items():
            sprites = PokemonSprites(**raw["sprites"])
            stats = PokemonStat(**raw["stats"])
            evolution = (
                PokemonEvolution(to=raw["evolution"]["to"], levelCap=raw["evolution"]["level"])
                if raw["evolution"]
                else None
            )
            pokemons[name] = PokemonProfile(
                baseExp=raw.get("baseExp", 0),
                catch_rate=raw.get("catchRate", 45),
                abilities=raw.get("abilities", []),
                types=raw.get("types", []),
                evolution=evolution,
                sprites=sprites,
                stats=stats,
            )
        return pokemons

    @staticmethod
    def parse_moves(data: dict) -> dict[str, PokemonMove]:
        moves = {}
        for name, raw in data.items():
            effects = [
                PokemonMoveEffect(
                    target=e["target"],
                    type=e["type"],
                    stat=e.get("stat"),
                    change=e.get("change"),
                    condition=e.get("condition"),
                    chance=e.get("chance"),
                )
                for e in raw["effects"]
            ]
            moves[name] = PokemonMove(
                name=name,
                category=raw["category"],
                type=raw["type"],
                power=raw["power"],
                accuracy=raw["accuracy"],
                pp=raw["pp"],
                effects=effects,
            )
        return moves

    @staticmethod
    def parse_items(data: dict) -> dict[str, ItemProfile]:
        items = {}
        for name, raw in data.items():
            effects = [
                ItemEffect(
                    type=e["type"],
                    amount=e.get("amount"),
                    catch_rate=e.get("catchRate"),
                )
                for e in raw["effects"]
            ]
            items[name] = ItemProfile(
                description=raw["description"],
                price=raw["price"],
                effects=effects,
            )
        return items

    @staticmethod
    def parse_npc_dialog(data: dict) -> dict[str, NpcProfile]:
        npc_dialogs = {}
        for name, npc_dialog in data.items():
            npc_dialogs[name] = NpcProfile(npc_dialog)
        return npc_dialogs
