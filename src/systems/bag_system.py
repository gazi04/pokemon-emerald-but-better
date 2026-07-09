from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from src.enums.effect_type import EffectType
from src.model.static.pokemon import PokemonStat


class BagSystem:
    def __init__(self, player_manager: PlayerManager, data_loader: DataLoader):
        self.player_manager = player_manager
        self.data_loader    = data_loader

        self._items       = player_manager.player.items.get("items", [])
        self._pokeballs   = player_manager.player.items.get("pokeballs", [])
        self._berries     = player_manager.player.items.get("berries", [])
        self._held_items  = player_manager.player.items.get("held_items", [])

        self._effect_appliers = {
            EffectType.HEAL:        self._apply_heal,
            EffectType.CURE_STATUS: self._apply_cure_status,
            EffectType.RESTORE_PP:  self._apply_restore_pp,
            EffectType.STAT_BOOST:  self._apply_stat_boost,
        }

        self._effect_eligibility = {
            EffectType.HEAL:        self._heal_eligible,
            EffectType.CURE_STATUS: self._cure_status_eligible,
            EffectType.RESTORE_PP:  self._restore_pp_eligible,
        }

    # ── Eligibility checks ────────────────────────────────────────────────────

    @staticmethod
    def _heal_eligible(pokemon, max_hp: int, effect) -> bool:
        return 0 < pokemon.hp < max_hp

    @staticmethod
    def _cure_status_eligible(pokemon, max_hp: int, effect) -> bool:
        return pokemon.status_condition is not None

    @staticmethod
    def _restore_pp_eligible(pokemon, max_hp: int, effect) -> bool:
        return any(
            move.pp < move.max_pp
            for move in pokemon.moves
        )

    # ── Appliers ──────────────────────────────────────────────────────────────

    def _apply_heal(self, pokemon_id: str, pokemon, max_hp: int, effect) -> bool:
        if not self._heal_eligible(pokemon, max_hp, effect):
            return False

        if effect.full_restore:
            new_hp = max_hp
        elif effect.percent:
            new_hp = min(pokemon.hp + int(max_hp * effect.percent / 100), max_hp)
        else:
            new_hp = min(pokemon.hp + effect.amount, max_hp)

        self.player_manager.update_pokemon_hp(pokemon_id, new_hp)
        return True

    def _apply_cure_status(self, pokemon_id: str, pokemon, max_hp: int, effect) -> bool:
        if not self._cure_status_eligible(pokemon, max_hp, effect):
            return False

        if effect.status == "all" or effect.status == pokemon.status_condition:
            self.player_manager.update_pokemon_status(pokemon_id, None)
            return True

        return False

    def _apply_restore_pp(self, pokemon_id: str, pokemon, max_hp: int, effect) -> bool:
        if not self._restore_pp_eligible(pokemon, max_hp, effect):
            return False

        for move in pokemon.moves:
            if move.pp < move.max_pp:
                new_pp = min(move.pp + effect.amount, move.max_pp)
                self.player_manager.update_pokemon_move_pp(pokemon_id, move.name, new_pp)

        return True

    def _apply_stat_boost(self, pokemon_id: str, pokemon, max_hp: int, effect) -> bool:
        # Stat boosts from bag items (outside battle) are permanent EV-style
        # In battle this is handled by BattleSystem, not BagSystem
        return True

    # ── Core item use ─────────────────────────────────────────────────────────

    def use_item(self, item_index: int, pokemon_id: str) -> bool:
        item_stack = self._items[item_index]
        item_def   = self.data_loader.get_item(item_stack.name)

        if not item_def:
            return False

        if self._handle_item_effects(pokemon_id.lower(), item_stack.name):
            self.player_manager.consume_item(item_stack.name)
            return True

        return False

    def use_pokeball(self, pokeball_index: int):
        if 0 <= pokeball_index < len(self._pokeballs):
            pokeball = self._pokeballs[pokeball_index]
            if pokeball.count > 0:
                self.player_manager.consume_pokeball(pokeball.name)
                return self.data_loader.get_item(pokeball.name)
        return None

    def can_use_item(self, item_index: int, pokemon_id: str) -> bool:
        if not self._items:
            return False

        inventory_item = self._items[item_index]
        pokemon        = self.player_manager.player.get_pokemon(pokemon_id)
        if not pokemon:
            return False

        pokemon_profile = self.data_loader.get_pokemon(pokemon.name)
        max_hp          = PokemonStat.max_hp(pokemon_profile.stats.hp, pokemon.level)
        item_def        = self.data_loader.get_item(inventory_item.name)

        return all(
            not (check := self._effect_eligibility.get(effect.type)) or check(pokemon, max_hp, effect)
            for effect in item_def.effects
        )

    def _handle_item_effects(self, pokemon_id: str, item_name: str) -> bool:
        pokemon = self.player_manager.player.get_pokemon(pokemon_id)
        if not pokemon:
            return False

        pokemon_profile = self.data_loader.get_pokemon(pokemon_id)
        max_hp          = PokemonStat.max_hp(pokemon_profile.stats.hp, pokemon.level)
        item_def        = self.data_loader.get_item(item_name)

        return all(
            not (applier := self._effect_appliers.get(effect.type)) or applier(pokemon_id, pokemon, max_hp, effect)
            for effect in item_def.effects
        )

    # ── Held item support ─────────────────────────────────────────────────────

    def give_held_item(self, item_name: str, pokemon_id: str) -> bool:
        """Assign a held item to a pokemon and remove it from the bag."""
        pokemon = self.player_manager.player.get_pokemon(pokemon_id)
        if not pokemon:
            return False

        item_def = self.data_loader.get_item(item_name)
        if not item_def or not item_def.holdable:
            return False

        if pokemon.held_item:
            # Return current held item to bag before replacing
            self.player_manager.add_item(pokemon.held_item)

        self.player_manager.update_pokemon_held_item(pokemon_id, item_name)
        self.player_manager.consume_item(item_name)
        return True

    def take_held_item(self, pokemon_id: str) -> bool:
        """Remove a pokemon's held item and return it to the bag."""
        pokemon = self.player_manager.player.get_pokemon(pokemon_id)
        if not pokemon or not pokemon.held_item:
            return False

        self.player_manager.add_item(pokemon.held_item)
        self.player_manager.update_pokemon_held_item(pokemon_id, None)
        return True

    # ── Getters ───────────────────────────────────────────────────────────────

    def get_items(self)     -> list: return self._items
    def get_pokeballs(self) -> list: return self._pokeballs
    def get_berries(self)   -> list: return self._berries
    def get_held_items(self)-> list: return self._held_items