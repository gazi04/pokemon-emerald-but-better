from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from src.model.battle.effect_type import EffectType
from src.model.static.pokemon import PokemonStat


class BagSystem:
    def __init__(self, player_manager: PlayerManager, data_loader: DataLoader):
        self.player_manager = player_manager
        self.data_loader = data_loader

        self._items = player_manager.player.items
        self._pokeballs = player_manager.player.pokeballs

    def use_pokeball(self, pokeball_index: int):
        if 0 <= pokeball_index < len(self._pokeballs):
            pokeball = self._pokeballs[pokeball_index]
            if pokeball.count > 0:
                name = pokeball.name
                self.player_manager.consume_pokeball(name)
                return self.data_loader.get_item(name)

        return None

    def use_item(self, itemIndex: int, pokemonId: str):
        if len(self._items) <= 0:
            return

        item = self._items[itemIndex]

        if self._handleItemEffects(pokemonId.lower(), item.name):
            self.player_manager.consume_item(item.name)

    def _handleItemEffects(self, pokemonId: str, itemId: str) -> bool:
        pokemon = self.player_manager.player.get_pokemon(pokemonId)
        if not pokemon:
            return False

        pokemonProfile = self.data_loader.get_pokemon(pokemonId)
        maxHp = PokemonStat.max_hp(pokemonProfile.stats.hp, pokemon.level)

        item = self.data_loader.get_item(itemId)

        for effect in item.effects:
            if effect.type == EffectType.HEAL:
                if pokemon.hp <= 0 or pokemon.hp == maxHp:
                    return False

                new_hp = min(pokemon.hp + effect.amount, maxHp)
                self.player_manager.update_pokemon_hp(pokemonId, new_hp)

        return True

    def can_use_item(self, itemIndex: int, pokemonId: str) -> bool:
        if len(self._items) <= 0:
            return False

        inventory_item = self._items[itemIndex]

        pokemon = self.player_manager.player.get_pokemon(pokemonId)
        pokemonProfile = self.data_loader.get_pokemon(pokemon.name)

        maxHp = PokemonStat.max_hp(pokemonProfile.stats.hp, pokemon.level)

        item_def = self.data_loader.get_item(inventory_item.name)
        for effect in item_def.effects:
            if effect.type == EffectType.HEAL:
                if pokemon.hp <= 0 or pokemon.hp == maxHp:
                    return False

        return True

    def get_items(self):
        return self._items

    def get_pokeballs(self):
        return self._pokeballs
