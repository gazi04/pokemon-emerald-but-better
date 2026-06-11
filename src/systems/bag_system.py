from src.core.data_loader import DataLoader
from src.core.save_manager import SaveManager


class BagSystem:
    def __init__(self, save_manager: SaveManager, data_loader: DataLoader):
        self.save_manager = save_manager
        self.data_loader = data_loader

        self._items = save_manager.player.items
        self._pokeballs = save_manager.player.pokeballs
        
    def usePokeball(self, pokeball_index: int):
        if 0 <= pokeball_index < len(self._pokeballs):
            pokeball = self._pokeballs[pokeball_index]
            if pokeball.count > 0:
                pokeball.count -= 1
                if pokeball.count <= 0:
                    self._pokeballs.pop(pokeball_index)
                    
                return self.data_loader.getItem(pokeball.name)
            
        return None

    def useItem(self, itemIndex: int, pokemonId: str):
        if len(self._items) <= 0:
            return

        item = self._items[itemIndex]

        if self._handleItemEffects(pokemonId.lower(), item.name):
            item.count -= 1
            if item.count <= 0:
                self._items.pop(itemIndex)

    def _handleItemEffects(self, pokemonId: str, itemId: str) -> bool:
        pokemon = self.save_manager.getPokemon(pokemonId)
        pokemonProfile = self.data_loader.getPokemon(pokemonId)

        maxHp = (
            ((2 * pokemonProfile.stats.hp * pokemon.level) // 100) + 5 + pokemon.level
        )

        if not pokemon:
            return False

        item = self.data_loader.getItem(itemId)

        for effect in item.effects:
            if effect.type == "heal":
                if pokemon.hp <= 0 or pokemon.hp == maxHp:
                    return False

                pokemon.hp += effect.amount
                if pokemon.hp > maxHp:
                    pokemon.hp = maxHp

        return True

    def canUseItem(self, itemIndex: int, pokemonId: str) -> bool:
        if len(self._items) <= 0:
            return False

        item = self._items[itemIndex]

        pokemon = self.save_manager.getPokemon(pokemonId)
        pokemonProfile = self.data_loader.getPokemon(pokemon.name)

        maxHp = (
            ((2 * pokemonProfile.stats.hp * pokemon.level) // 100) + 5 + pokemon.level
        )

        for effect in item.effects:
            if effect.type == "heal":
                if pokemon.hp <= 0 or pokemon.hp == maxHp:
                    return False

        return True

    def getItems(self):
        return self._items

    def getPokeballs(self):
        return self._pokeballs
