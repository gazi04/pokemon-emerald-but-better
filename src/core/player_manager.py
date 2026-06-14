from src.core.save_manager import SaveManager
from src.model.player import PlayerProfile, PlayerPokemon, Item
from typing import Optional

class PlayerManager:
    def __init__(self, save_manager: SaveManager):
        self.save_manager = save_manager
        self.player: Optional[PlayerProfile] = save_manager.player

    def add_money(self, amount: int) -> int:
        self.player.money += amount
        return self.player.money
    
    def remove_money(self, amount: int) -> bool:
        if self.player.money >= amount:
            self.player.money -= amount
            return True
        return False
    
    def update_pokemon_hp(self, pokemon_name: str, hp: int):
        self.player.update_hp(pokemon_name, hp)
        
    def update_move_pp(self, pokemon_name: str, move_name: str, pp: int):
        self.player.update_move_pp(pokemon_name, move_name, pp)
        
    def update_level(self, pokemon_name: str, new_level: int, exp: int, evolved_name: str = None):
        self.player.update_level(pokemon_name, new_level, exp, evolved_name)
    
    def add_pokemon(self, pokemon: PlayerPokemon) -> bool:
        return self.player.add_pokemon(pokemon)
    
    def mark_seen(self, pokemon_name: str):
        self.player.mark_seen(pokemon_name)
    
    def add_item(self, name: str, count: int) -> bool:
        for item in self.player.items:
            if item.name == name:
                item.count += count
                return True
        self.player.items.append(Item(name, count))
        return True

    def get_money(self) -> int:
        return self.player.money

    def get_pokemon(self, name: str) -> Optional[PlayerPokemon]:
        return self.player.get_pokemon(name)

    def get_pokemon_team(self) -> list[PlayerPokemon]:
        return self.player.pokemon

    def get_seen_pokemon(self) -> list[str]:
        return self.player.seen

    def get_inventory(self) -> list[Item]:
        return self.player.items