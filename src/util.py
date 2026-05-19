import json
from src.core.saveManager import SaveManager
from src.core.dataLoader import DataLoader
from src.model.player import PlayerProfile

# Global cached instances
save_manager = SaveManager()
data_loader = DataLoader()


def loadPlayer():
    return save_manager.get_player().model_dump()


def savePlayer(data):
    save_manager.player_profile = PlayerProfile(**data)
    save_manager.save()


def getTeamPokemon(player_data, name):
    for p in player_data["pokemons"]:
        if p["name"] == name:
            return p
    return None


def getPokemon():
    return {k: v.model_dump() for k, v in data_loader.pokemons.items()}


def getPlayersPokemon():
    pokemons = loadPlayer()["pokemons"]
    allPokemons = getPokemon()
    result = []
    for p in pokemons:
        merged = {**p, **allPokemons[p["name"]]}
        result.append(merged)
    return result


def getPlayerItems():
    playerItems = loadPlayer()["items"]
    allItems = data_loader.items
    result = []
    for item in playerItems:
        result.append({**item, **allItems[item["name"]]})
    return result


def getPlayerPokeball():
    playerPokeball = loadPlayer()["pokeballs"]
    allItems = data_loader.items
    result = []
    for item in playerPokeball:
        result.append({**item, **allItems[item["name"]]})
    return result


def updateHp(name, newHp):
    data = loadPlayer()
    pokemon = getTeamPokemon(data, name.lower())
    if pokemon:
        pokemon["hp"] = max(0, newHp)
    savePlayer(data)


def updateMove(name, moves):
    data = loadPlayer()
    pokemon = getTeamPokemon(data, name.lower())
    for move in moves:
        for pokemonMove in pokemon["moves"]:
            if move["name"] == pokemonMove["name"]:
                pokemonMove["pp"] = move["pp"]
    savePlayer(data)


def updateLevel(name, level, exp, evolvedName=None):
    data = loadPlayer()
    pokemon = getTeamPokemon(data, name.lower())
    pokemon["level"] = level
    pokemon["exp"] = exp
    if evolvedName:
        pokemon["name"] = evolvedName
    savePlayer(data)


def getConfigs():
    with open("data/config.json", "r") as f:
        return json.load(f)


def getEnc():
    with open("data/encounters.json", "r") as f:
        return json.load(f)


def getAMove(name):
    try:
        move = data_loader.get_move(name)
        if move:
            return move.model_dump()
        return {}
    except Exception as e:
        print(f"Unhandled exception occurred: {e}")
        return {}


def calculateMultiplier(atk_type, def_types):
    with open("data/types.json", "r") as f:
        type_data = json.load(f)
    multiplier = 1.0
    for type in def_types:
        multiplier *= type_data.get(atk_type, {}).get(type, 1.0)
    return multiplier
