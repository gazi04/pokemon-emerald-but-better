from src.model.save.player import (
    PlayerSave,
    PlayerPokemon,
    PlayerPokemonMove,
    ItemStack,
    Box
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
            items[key] = ItemStack(
                key, item["count"], ItemCategory(item["category"]))

        boxs = []
        for item in data["box"]:
            _pokemons = []
            for pokemon in item["pokemons"]:
                moves = [
                    PlayerPokemonMove(name=m["name"], pp=m["pp"]) for m in pokemon["moves"]
                ]

                _pokemons.append(
                    PlayerPokemon(
                        name=pokemon["name"],
                        hp=pokemon["hp"],
                        level=pokemon["level"],
                        exp=pokemon["exp"],
                        ability=pokemon["ability"],
                        held_item=pokemon["held_item"],
                        moves=moves,
                        status_condition=pokemon.get(
                            "status_condition"),
                    )
                )

            boxs.append(Box(item["box_name"], _pokemons))

        seen = data.get("seen", [])

        return PlayerSave(
            pokemon=pokemons,
            items=items,
            seen=seen,
            money=data.get("money", 0),
            boxs=boxs,
            npc_states=data.get("npc_states", []),
            collected_items=data.get("collected_items", []),
        )

    @staticmethod
    def serialize(player: PlayerSave, motion: PlayerMotion | None = None) -> dict:
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

        boxs = []
        for box in player.boxs:
            _pokemons = []
            for pokemon in box.pokemons:
                moves = [{"name": m.name, "pp": m.pp} for m in pokemon.moves]
                _pokemons.append(
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
            
            boxs.append({"box_name": box.name, "pokemons": _pokemons})

        data = {
            "pokemons": pokemons,
            "items": items,
            "seen": list(player.seen),
            "money": player.money,
            "box": boxs,
            "npc_states": player.npc_states,
            "collected_items": list(player.collected_items),
        }
        if motion is not None:
            data["position"] = PlayerSerializer.position(motion)
        return data
