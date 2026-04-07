import json

def getPokemon():
    with open("data/pokemon.json", "r") as f:
        poke = json.load(f)
        
    return poke

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
    except:
        print("The move doesnt exits")
        return {}