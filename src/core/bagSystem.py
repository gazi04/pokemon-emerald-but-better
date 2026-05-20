from src.core.gameContext import saveManager, dataLoader
from src.model.item import Item


class BagSystem:
    def __init__(self):
        self._items = saveManager.player.items
        self._pokeballs = saveManager.player.pokeballs
<<<<<<< HEAD
    
    def useItem(self, itemIndex: int, pokemonId: str):
=======

    def useItem(self, itemIndex: int):
>>>>>>> 70b8707649d05718ddc8b9fe20909b301db59851
        if len(self._items) <= 0:
            return

        item = self._items[itemIndex]
<<<<<<< HEAD
        
        if self._handleItemEffects(pokemonId.lower(), item.name):
            item.count -= 1
            if item.count <= 0:
                self._items.pop(itemIndex)
    
    def _handleItemEffects(self, pokemonId:str, itemId:str) -> bool:
=======
        item.count -= 1
        if item.count <= 0:
            self._items.pop(itemIndex)

        self._handleItemEffects("combusken", item.name)

    def _handleItemEffects(self, pokemonId: str, itemId: str):
>>>>>>> 70b8707649d05718ddc8b9fe20909b301db59851
        pokemon = saveManager.getPokemon(pokemonId)
        pokemonProfile = dataLoader.getPokemon(pokemonId)
        
        maxHp = ((2 * pokemonProfile.stats.hp * pokemon.level) // 100) + 5 + pokemon.level
        
        if not pokemon:
<<<<<<< HEAD
            return False
        
=======
            return

>>>>>>> 70b8707649d05718ddc8b9fe20909b301db59851
        item = dataLoader.getItem(itemId)

        for effect in item.effects:
            if effect.type == "heal":
                if pokemon.hp <= 0 or pokemon.hp == maxHp:
                    return False
                
                pokemon.hp += effect.amount
<<<<<<< HEAD
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
                
=======

>>>>>>> 70b8707649d05718ddc8b9fe20909b301db59851
    def getItems(self):
        return self._items

    def getPokeballs(self):
        return self._pokeballs
