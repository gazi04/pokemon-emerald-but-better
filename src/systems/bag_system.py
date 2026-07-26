from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from src.enums.effect_type import EffectType
from src.enums.item_category import ItemCategory
from src.model.static.pokemon import PokemonStat
from src.model.static.item import ItemSpecies, ItemEffect
from src.model.save.player import ItemStack, PlayerPokemon


class BagSystem:
    def __init__(self, player_manager: PlayerManager, data_loader: DataLoader):
        self.player_manager = player_manager
        self.data_loader = data_loader

        self._items = player_manager.player.items

        self._effect_appliers = {
            EffectType.HEAL: self._apply_heal,
            EffectType.CURE_STATUS: self._apply_cure_status,
            EffectType.RESTORE_PP: self._apply_restore_pp,
        }

        self._effect_eligibility = {
            EffectType.HEAL: self._heal_eligible,
            EffectType.CURE_STATUS: self._cure_status_eligible,
            EffectType.RESTORE_PP: self._restore_pp_eligible,
        }

    # ── Eligibility checks ────────────────────────────────────────────────────

    def _heal_eligible(
        self, pokemon: PlayerPokemon, max_hp: int, effect: ItemEffect
    ) -> bool:
        return 0 < pokemon.hp < max_hp

    def _cure_status_eligible(
        self, pokemon: PlayerPokemon, max_hp: int, effect: ItemEffect
    ) -> bool:
        return pokemon.status_condition is not None

    def _restore_pp_eligible(
        self, pokemon: PlayerPokemon, max_hp: int, effect: ItemEffect
    ) -> bool:
        return any(move.pp < self._max_pp(move) for move in pokemon.moves)

    def _max_pp(self, move) -> int:
        """A move's max PP comes from its species data — the single source of
        truth — not a field duplicated on the save."""
        move_data = self.data_loader.get_move(move.name.lower())
        return move_data.pp if move_data else move.pp

    # ── Appliers ──────────────────────────────────────────────────────────────

    def _apply_heal(
        self,
        pokemon_id: str,
        pokemon: PlayerPokemon,
        max_hp: int,
        effect: ItemEffect,
        move_index=None,
    ) -> bool:
        if not self._heal_eligible(pokemon, max_hp, effect):
            return False

        if effect.full_restore:
            new_hp = max_hp
        elif effect.percent:
            new_hp = min(pokemon.hp + int(max_hp * effect.percent / 100), max_hp)
        elif effect.amount is not None:
            new_hp = min(pokemon.hp + effect.amount, max_hp)
        else:
            # A heal effect with no full_restore/percent/amount is malformed;
            # don't consume the item over bad data.
            return False

        self.player_manager.update_pokemon_hp(pokemon_id, new_hp)
        return True

    def _apply_cure_status(
        self,
        pokemon_id: str,
        pokemon: PlayerPokemon,
        max_hp: int,
        effect: ItemEffect,
        move_index=None,
    ) -> bool:
        if not self._cure_status_eligible(pokemon, max_hp, effect):
            return False

        if effect.status == "all" or effect.status == pokemon.status_condition:
            self.player_manager.update_pokemon_status(pokemon_id, None)
            return True

        return False

    def _apply_restore_pp(
        self,
        pokemon_id: str,
        pokemon: PlayerPokemon,
        max_hp: int,
        effect: ItemEffect,
        move_index=None,
    ) -> bool:
        """Restore PP to a single chosen move (Ether/Leppa). A missing
        move_index means "all moves" (Elixir-style items)."""
        if effect.amount is None:
            return False

        if move_index is None:
            targets = range(len(pokemon.moves))
        elif 0 <= move_index < len(pokemon.moves):
            targets = [move_index]
        else:
            return False

        restored = False
        for i in targets:
            move = pokemon.moves[i]
            max_pp = self._max_pp(move)
            if move.pp < max_pp:
                new_pp = min(move.pp + effect.amount, max_pp)
                self.player_manager.update_move_pp(pokemon_id, move.name, new_pp)
                restored = True

        return restored

    # ── Core item use ─────────────────────────────────────────────────────────

    def use_item(
        self, item_id: str, pokemon_id: str, move_index: int | None = None
    ) -> bool:
        if self._handle_item_effects(pokemon_id.lower(), item_id, move_index):
            self.player_manager.consume_item(item_id)
            return True

        return False

    def is_pp_item(self, item_id: str) -> bool:
        """True if the item restores PP (so a move must be chosen for it)."""
        item = self.data_loader.get_item(item_id)
        return bool(item) and any(e.type == EffectType.RESTORE_PP for e in item.effects)

    def use_pokeball(self, pokeball_id: str) -> ItemSpecies | None:
        pokeball = self._items.get(pokeball_id)

        if (
            pokeball
            and pokeball.count > 0
            and pokeball.category == ItemCategory.POKEBALL
        ):
            self.player_manager.consume_item(pokeball.name)
            return self.data_loader.get_item(pokeball.name)

        return None

    def _handle_item_effects(
        self, pokemon_id: str, item_name: str, move_index: int | None = None
    ) -> bool:
        pokemon = self.player_manager.player.get_pokemon(pokemon_id)
        if not pokemon:
            return False

        pokemon_profile = self.data_loader.require_pokemon(pokemon_id)
        max_hp = PokemonStat.max_hp(pokemon_profile.stats.hp, pokemon.level)
        item_def = self.data_loader.require_item(item_name)

        return all(
            not (applier := self._effect_appliers.get(effect.type))
            or applier(pokemon_id, pokemon, max_hp, effect, move_index)
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
            return False

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

    def get_items(self) -> dict[str, list[ItemStack]]:
        result: dict[str, list[ItemStack]] = {}

        for stack in self._items.values():
            if stack.count <= 0:
                continue

            if stack.category not in result:
                result[stack.category] = []

            result[stack.category].append(stack)

        return result
