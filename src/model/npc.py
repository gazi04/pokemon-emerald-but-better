from dataclasses import dataclass
from typing import Optional
from src.model.player import PlayerPokemon, PlayerPokemonMove

@dataclass
class NpcProfile:
    dialog: list[str]
    action_after_dialog: str
    team: list[PlayerPokemon]
    
    def __init__(self, data):
        self.dialog = data["dialog"]
        self.action_after_dialog = data["action_after_dialog"]
        self.team = []
        
        for pokemon in data.get("team", []):
            moves = [PlayerPokemonMove(move["name"], move["pp"]) for move in pokemon["moves"]]
            
            self.team.append(
                PlayerPokemon(
                    pokemon["name"], 
                    pokemon["hp"], 
                    pokemon["level"], 
                    0, 
                    moves
                )
            )