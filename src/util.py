import json

def getPokemon():
    with open("data/pokemon.json", "r") as f:
        poke = json.load(f)
        
    return poke

def getAMove(name):
    try:
        with open("data/moves.json", "r") as f:
            return json.load(f)[name]
    except:
        print("The move doesnt exits")
        return {}