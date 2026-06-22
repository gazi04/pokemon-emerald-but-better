from src.model.static.pokemon import (
    PokemonSpecies,
    SpritePaths,
    PokemonStat,
    PokemonMove,
    PokemonMoveEffect,
    PokemonEvolution,
)
from src.model.static.item import ItemSpecies, ItemEffect
from src.model.static.npc import NpcSpecies
from src.model.static.trainer import Trainer


class GameDataParser:
    @staticmethod
    def parse_pokemons(data: dict) -> dict[str, PokemonSpecies]:
        pokemons = {}
        for name, raw in data.items():
            sprites = SpritePaths(**raw["sprites"])
            stats = PokemonStat(**raw["stats"])
            evolution = (
                PokemonEvolution(to=raw["evolution"]["to"], levelCap=raw["evolution"]["level"])
                if raw["evolution"]
                else None
            )
            pokemons[name] = PokemonSpecies(
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
    def parse_items(data: dict) -> dict[str, ItemSpecies]:
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
            items[name] = ItemSpecies(
                description=raw["description"],
                price=raw["price"],
                effects=effects,
            )
        return items

    @staticmethod
    def parse_npc_dialog(data: dict) -> dict[str, NpcSpecies]:
        npcs = {}
        for name, raw in data.items():
            block = raw.get("dialog", {})
            # "dialog" is normally a {state: [lines]} dict; tolerate the legacy
            # flat list form by mapping it to the default state.
            dialogs = {"default": block} if isinstance(block, list) else dict(block)
            npcs[name] = NpcSpecies(
                name=raw.get("name", ""),
                dialogs=dialogs,
                action_after_dialog=raw.get("action_after_dialog", "end"),
                team=Trainer(raw.get("team", [])),
            )
        return npcs
