import json
from src.model.pokemon import PokemonProfile, PokemonSprites, PokemonStat, PokemonMove, PokemonMoveEffect
from src.model.item import Item, ItemEffect

class DataLoader:
    def __init__(self):
        self.pokemons = []
        self.moves = []
        self.items = []
        
        self.loadPokemons()
        self.loadMoves()
        self.loadItems()
    
    def loadPokemons(self):
        with open("data/pokemon.json", "r") as f:
            data = json.load(f)
            
        for pokemon in data:
            sprites = PokemonSprites(pokemon["sprites"]["back"], pokemon["sprites"]["front"])
            stats = PokemonStat(
                pokemon["hp"], 
                pokemon["attack"],
                pokemon["defence"],
                pokemon["special_attack"],
                pokemon["special_defence"],
                pokemon["speed"]
            )
            
            self.pokemons.append(PokemonProfile(
                pokemon["baseExp"], 
                pokemon["evolution"],
                sprites,
                pokemon["abilities"],
                pokemon["types"],
                stats
            ))
    
    def loadMoves(self):
        with open("data/moves.json", "r") as f:
            data = json.load(f)
            
        for move in data:
            effects = []
            
            for effect in move["effects"]:
                effects.append(PokemonMoveEffect(
                    effect["target"],
                    effect["type"],
                    effect["stat"],
                    effect["change"],
                    effect["condition"],
                    effect["chance"]
                ))
            
            self.moves.append(PokemonMove(
                move["category"],
                move["type"],
                move["power"],
                move["accuracy"],
                move["pp"],
                effects
            ))
    
    def loadItems(self):
        with open("data/items.json", "r") as f:
            data = json.load(f)
            
        for item in data:
            effects = []
            
            for effect in item["effects"]:
                effects.append(ItemEffect(
                    effect["type"],
                    effect["amount"],
                    effect["catchRate"]
                ))
            
            self.items.append(Item(
                item["description"],
                item["price"],
                effects
            ))