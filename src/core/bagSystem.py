from src.core.gameContext import saveManager, dataLoader
from src.model.item import Item


class BagSystem:
    def __init__(self):
        self._items = saveManager.player.items
        self._pokeballs = saveManager.player.pokeballs
    
    def useItem(self, itemIndex: int, pokemonId: str):
        if len(self._items) <= 0:
            return

        item = self._items[itemIndex]
        
        if self._handleItemEffects(pokemonId.lower(), item.name):
            item.count -= 1
            if item.count <= 0:
                self._items.pop(itemIndex)
    
    def _handleItemEffects(self, pokemonId:str, itemId:str) -> bool:
        pokemon = saveManager.getPokemon(pokemonId)
        pokemonProfile = dataLoader.getPokemon(pokemonId)
        
        maxHp = ((2 * pokemonProfile.stats.hp * pokemon.level) // 100) + 5 + pokemon.level
        
        if not pokemon:
            return False
        
        item = dataLoader.getItem(itemId)

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
        
        pokemon = saveManager.getPokemon(pokemonId)
        pokemonProfile = dataLoader.getPokemon(pokemon.name)
        
        maxHp = ((2 * pokemonProfile.stats.hp * pokemon.level) //
                     100) + 5 + pokemon.level
        
        for effect in item.effects:
            if effect.type == "heal":
                if pokemon.hp <= 0 or pokemon.hp == maxHp:
                    return False
        
        return True
                
    def getItems(self):
        return self._items

    def getPokeballs(self):
        return self._pokeballs
