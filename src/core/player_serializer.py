from typing import Optional

from src.model.save.player import (
    PlayerSave,
    PlayerPokemon,
    PlayerPokemonMove,
    ItemStack,
)
from src.model.motion.player_motion import PlayerMotion
from src.enums.item_category import ItemCategory


class PlayerSerializer:
    @staticmethod
    def position(motion: PlayerMotion) -> dict:
        """The single definition of the saved position schema."""
        return {
            "map_name": motion.map_name,
            "direction": motion.direction,
            "pixel_x": motion.pixel_x,
            "pixel_y": motion.pixel_y,
        }

    @staticmethod
    def deserialize(data: dict) -> PlayerSave:
        pokemons = []
        for pokemon in data["pokemons"]:
            moves = [
                PlayerPokemonMove(name=m["name"], pp=m["pp"]) for m in pokemon["moves"]
            ]
            pokemons.append(
                PlayerPokemon(
                    name=pokemon["name"],
                    hp=pokemon["hp"],
                    level=pokemon["level"],
                    exp=pokemon["exp"],
                    ability=pokemon["ability"],
                    held_item=pokemon["held_item"],
                    moves=moves,
                    status_condition=pokemon.get("status_condition"),
                )
            )

        items = {}
        for key, item in data["items"].items():
            items[key] = ItemStack(key, item["count"], ItemCategory(item["category"]))

        seen = data.get("seen", [])

        return PlayerSave(
            pokemon=pokemons,
            items=items,
            seen=seen,
            money=data.get("money", 0),
            npc_states=data.get("npc_states", []),
            collected_items=data.get("collected_items", []),
        )

    @staticmethod
    def serialize(player: PlayerSave, motion: Optional[PlayerMotion] = None) -> dict:
        pokemons = []
        for pokemon in player.pokemon:
            moves = [{"name": m.name, "pp": m.pp} for m in pokemon.moves]
            pokemons.append(
                {
                    "name": pokemon.name,
                    "hp": pokemon.hp,
                    "level": pokemon.level,
                    "exp": pokemon.exp,
                    "ability": pokemon.ability,
                    "held_item": pokemon.held_item,
                    "status_condition": pokemon.status_condition,
                    "moves": moves,
                }
            )

        # Mirror deserialize: items is a dict keyed by item id.
        items = {
            item_id: {"count": stack.count, "category": stack.category}
            for item_id, stack in player.items.items()
        }

        data = {
            "pokemons": pokemons,
            "items": items,
            "seen": list(player.seen),
            "money": player.money,
            "npc_states": player.npc_states,
            "collected_items": list(player.collected_items),
        }
        if motion is not None:
            data["position"] = PlayerSerializer.position(motion)
        return data
