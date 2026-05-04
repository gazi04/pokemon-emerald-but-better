import json
from functools import lru_cache

PLAYER_FILE = "data/player.json"


def loadPlayer():
    with open(PLAYER_FILE, "r") as f:
        return json.load(f)


def savePlayer(data):
    with open(PLAYER_FILE, "w") as f:
        json.dump(data, f, indent=4)


def getTeamPokemon(player_data, name):
    for p in player_data["pokemons"]:
        if p["name"] == name:
            return p
    return None


@lru_cache(maxsize=1)
def getPokemon():
    with open("data/pokemon.json", "r") as f:
        poke = json.load(f)

    return poke


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
    
    with open("data/items.json", "r") as f:
        allItems = json.load(f)
        
    result = []
    
    for item in playerItems:
        result.append({**item, **allItems[item["name"]]})
    
    return result

def getPlayerPokeball():
    playerPokeball = loadPlayer()["pokeballs"]
    
    with open("data/items.json", "r") as f:
        allItems = json.load(f)
        
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
        config = json.load(f)

    return config


def getEnc():
    with open("data/encounters.json", "r") as f:
        enc = json.load(f)

    return enc


def getAMove(name):
    try:
        with open("data/moves.json", "r") as f:
            return json.load(f)[name]
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
