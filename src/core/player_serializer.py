from src.model.player import PlayerProfile, PlayerPokemon, PlayerPokemonMove, InventoryStack, Pokeball


class PlayerSerializer:
    @staticmethod
    def deserialize(data: dict) -> PlayerProfile:
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

        items = [InventoryStack(item["name"], item["count"]) for item in data["items"]]
        pokeballs = [Pokeball(pb["name"], pb["count"]) for pb in data["pokeballs"]]
        seen = data.get("seen", [])

        return PlayerProfile(
            pokemon=pokemons, items=items, pokeballs=pokeballs, seen=seen
        )

    @staticmethod
    def serialize(player: PlayerProfile) -> dict:
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

        return {
            "pokemons": pokemons,
            "items": [{"name": i.name, "count": i.count} for i in player.items],
            "pokeballs": [
                {"name": pb.name, "count": pb.count} for pb in player.pokeballs
            ],
            "seen": list(player.seen),
        }
