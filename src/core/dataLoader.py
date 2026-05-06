import json
from src.model.pokemon import PokemonProfile, PokemonSprites, PokemonStat, PokemonMove, PokemonMoveEffect
from src.model.item import Item, ItemEffect

class DataLoader:
    def __init__(self):
        self.pokemons: dict[str, PokemonProfile] = {} 
        self.moves: dict[str, PokemonMove] = {}
        self.items: dict[str, Item] = {}
        
        self.loadPokemons()
        self.loadMoves()
        self.loadItems()
    
    def getAMove(self, name) -> PokemonMove | None:
        return self.moves.get(name)  
    
    def getPokemon(self, name) -> Item | None:
        return self.pokemons.get(name)  
    
    def getItem(self, name) -> Item | None:
        return self.items.get(name)  
    
    def loadPokemons(self):
        with open("data/pokemon.json", "r") as f:
            data = json.load(f)
            
        for name, pokemon in data.items():  
            sprites = PokemonSprites(pokemon["sprites"]["back"], pokemon["sprites"]["front"])
            stats = PokemonStat(
                pokemon["stats"]["hp"], 
                pokemon["stats"]["attack"],
                pokemon["stats"]["defence"],
                pokemon["stats"]["special_attack"],
                pokemon["stats"]["special_defence"],
                pokemon["stats"]["speed"]
            )
            
            self.pokemons[name] = PokemonProfile( 
                pokemon["baseExp"], 
                pokemon["evolution"],
                sprites,
                pokemon["abilities"],
                pokemon["types"],
                stats
            )
    
    def loadMoves(self):
        with open("data/moves.json", "r") as f:
            data = json.load(f)
            
        for name, move in data.items():
            effects = []
            
            for effect in move["effects"]:
                effects.append(PokemonMoveEffect(
                    effect["target"],
                    effect["type"],
                    effect.get("stat"),
                    effect.get("change"),
                    effect.get("condition"),
                    effect.get("chance")
                ))
            
            self.moves[name] = PokemonMove(   
                move["category"],
                move["type"],
                move["power"],
                move["accuracy"],
                move["pp"],
                effects
            )
    
    def loadItems(self):
        with open("data/items.json", "r") as f:
            data = json.load(f)
            
        for name, item in data.items():
            effects = []
            
            for effect in item["effects"]:
                effects.append(ItemEffect(
                    effect["type"],
                    effect.get("amount"),
                    effect.get("catchRate")
                ))
            
            self.items[name] = Item(        # Fix 4: assign to dict key
                item["description"],
                item["price"],
                effects
            )