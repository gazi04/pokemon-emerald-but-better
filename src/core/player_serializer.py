from typing import Optional

from src.model.save.player import PlayerSave, PlayerPokemon, PlayerPokemonMove, ItemStack
from src.model.motion.player_motion import PlayerMotion


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
                    moves=moves,
                )
            )

        items = [ItemStack(item["name"], item["count"]) for item in data["items"]]
        pokeballs = [ItemStack(pb["name"], pb["count"]) for pb in data["pokeballs"]]
        seen = data.get("seen", [])

        return PlayerSave(
            pokemon=pokemons,
            items=items,
            pokeballs=pokeballs,
            seen=seen,
            money=data.get("money", 0),
            npc_states=data.get("npc_states", []),
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
                    "moves": moves,
                }
            )

        data = {
            "pokemons": pokemons,
            "items": [{"name": i.name, "count": i.count} for i in player.items],
            "pokeballs": [
                {"name": pb.name, "count": pb.count} for pb in player.pokeballs
            ],
            "seen": list(player.seen),
            "money": player.money,
            "npc_states": player.npc_states,
        }
        if motion is not None:
            data["position"] = PlayerSerializer.position(motion)
        return data
