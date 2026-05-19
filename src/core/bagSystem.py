from src.core.gameContext import saveManager, dataLoader
from src.model.item import Item


class BagSystem:
    def __init__(self):
        self._items = saveManager.player.items
        self._pokeballs = saveManager.player.pokeballs

    def useItem(self, itemIndex: int):
        if len(self._items) <= 0:
            return

        item = self._items[itemIndex]
        item.count -= 1
        if item.count <= 0:
            self._items.pop(itemIndex)

        self._handleItemEffects("combusken", item.name)

    def _handleItemEffects(self, pokemonId: str, itemId: str):
        pokemon = saveManager.getPokemon(pokemonId)
        if not pokemon:
            return

        item = dataLoader.getItem(itemId)

        for effect in item.effects:
            if effect.type == "heal":
                pokemon.hp += effect.amount

    def getItems(self):
        return self._items

    def getPokeballs(self):
        return self._pokeballs
