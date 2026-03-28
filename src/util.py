import json

def getPokemon():
    with open("data/pokemon.json", "r") as f:
        poke = json.load(f)
        
    return poke