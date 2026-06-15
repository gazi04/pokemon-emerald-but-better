from dataclasses import dataclass
from src.model.player import PlayerPokemon, PlayerPokemonMove

@dataclass
class Trainer:
    party: list[PlayerPokemon]
    
    def __init__(self, data):
        self.party = []
        
        for pokemon in data:
            moves = [PlayerPokemonMove(move["name"], move["pp"]) for move in pokemon["moves"]]
            
            self.party.append(
                PlayerPokemon(
                    pokemon["name"], 
                    pokemon["hp"], 
                    pokemon["level"], 
                    0, 
                    moves
                )
            )