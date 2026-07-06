from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from src.enums.effect_type import EffectType
from src.model.static.pokemon import PokemonStat


class BagSystem:
    def __init__(self, player_manager: PlayerManager, data_loader: DataLoader):
        self.player_manager = player_manager
        self.data_loader = data_loader

        self._items = player_manager.player.items
        self._pokeballs = player_manager.player.pokeballs
        self._berries = player_manager.player.berries

        # Dispatch over effect.type — add an effect kind by adding an applier,
        # not by editing the loop (mirrors npc_behaviors.make_behavior).
        self._effect_appliers = {EffectType.HEAL: self._apply_heal}
        self._effect_eligibility = {EffectType.HEAL: self._heal_eligible}

    def use_pokeball(self, pokeball_index: int):
        if 0 <= pokeball_index < len(self._pokeballs):
            pokeball = self._pokeballs[pokeball_index]
            if pokeball.count > 0:
                name = pokeball.name
                self.player_manager.consume_pokeball(name)
                return self.data_loader.get_item(name)

        return None

    def use_item(self, item_index: str, pokemon_id: str):
        if len(self._items) <= 0:
            return

        if self._handle_item_effects(pokemon_id.lower(), item_index):
            self.player_manager.consume_item(item_index)

    @staticmethod
    def _heal_eligible(pokemon, max_hp: int) -> bool:
        """Healable only when alive and not already at full HP."""
        return 0 < pokemon.hp < max_hp

    def _apply_heal(self, pokemon_id: str, pokemon, max_hp: int, effect) -> bool:
        """Apply a HEAL effect. Returns False (and mutates nothing) if ineligible."""
        if not self._heal_eligible(pokemon, max_hp):
            return False
        new_hp = min(pokemon.hp + effect.amount, max_hp)
        self.player_manager.update_pokemon_hp(pokemon_id, new_hp)
        return True

    def _handle_item_effects(self, pokemon_id: str, item_id: str) -> bool:
        pokemon = self.player_manager.player.get_pokemon(pokemon_id)
        if not pokemon:
            return False

        pokemon_profile = self.data_loader.get_pokemon(pokemon_id)
        max_hp = PokemonStat.max_hp(pokemon_profile.stats.hp, pokemon.level)

        item = self.data_loader.get_item(item_id)

        for effect in item.effects:
            applier = self._effect_appliers.get(effect.type)
            if applier and not applier(pokemon_id, pokemon, max_hp, effect):
                return False

        return True

    def can_use_item(self, item_index: int, pokemon_id: str) -> bool:
        if len(self._items) <= 0:
            return False

        inventory_item = self._items[item_index]

        pokemon = self.player_manager.player.get_pokemon(pokemon_id)
        pokemon_profile = self.data_loader.get_pokemon(pokemon.name)

        max_hp = PokemonStat.max_hp(pokemon_profile.stats.hp, pokemon.level)

        item_def = self.data_loader.get_item(inventory_item.name)
        for effect in item_def.effects:
            check = self._effect_eligibility.get(effect.type)
            if check and not check(pokemon, max_hp):
                return False

        return True

    def get_items(self):
        return self._items

    def get_pokeballs(self):
        return self._pokeballs

    def get_berries(self):
        return self._berries