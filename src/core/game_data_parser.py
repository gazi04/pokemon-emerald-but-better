from src.model.static.pokemon import (
    PokemonSpecies,
    SpritePaths,
    PokemonStat,
    PokemonMove,
    PokemonMoveEffect,
    PokemonEvolution,
    LearnsetMove,
)
from src.model.static.item import ItemSpecies, ItemEffect
from src.model.static.npc import NpcSpecies
from src.model.static.trainer import Trainer
from src.model.static.ability import Ability
from src.enums.stat import Stat
from src.enums.status_effect import StatusEffect
from src.enums.effect_type import EffectType


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
                learnset=[
                    LearnsetMove(move=m["move"], level=m["level"])
                    for m in raw.get("learnset", [])
                ],
            )
        return pokemons

    @staticmethod
    def parse_moves(data: dict) -> dict[str, PokemonMove]:
        moves = {}
        for name, raw in data.items():
            effects = [
                PokemonMoveEffect(
                    target=e["target"],
                    type=EffectType(e["type"]),
                    stat=Stat(e["stat"]) if e.get("stat") else None,
                    change=e.get("change"),
                    condition=StatusEffect(e["condition"]) if e.get("condition") else None,
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
                priority=raw["priority"],
                crit=raw["crit"],
                multi_hit=raw["multi_hit"],
                effects=effects
            )
        return moves

    @staticmethod
    def parse_items(data: dict) -> dict[str, ItemSpecies]:
        items = {}
        for name, raw in data.items():
            effects = [
                ItemEffect(
                    type=EffectType(e["type"]),
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
    
    @staticmethod
    def parse_ability(data: dict) -> dict[str, Ability]:
        ability = {}
        
        for name, raw in data.items():
            ability[name] = Ability(raw)
        
        return ability
