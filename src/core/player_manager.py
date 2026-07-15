from src.core.save_manager import SaveManager
from src.core.data_loader import DataLoader
from src.model.save.player import (
    PlayerSave,
    PlayerPokemon,
    ItemStack,
    PlayerPokemonMove,
)
from src.model.static.pokemon import PokemonStat
from src.model.battle.battle_pokemon import BattlePokemon
from src.systems.npc_manager import NPCManager
from typing import Optional


class PlayerManager:
    def __init__(
        self, save_manager: SaveManager, data_loader: Optional[DataLoader] = None
    ):
        self.save_manager = save_manager
        self.data_loader = data_loader
        self.player: Optional[PlayerSave] = save_manager.player
        self.npc_manager = NPCManager()

        if (
            hasattr(save_manager.player, "npc_states")
            and save_manager.player.npc_states
        ):
            self.npc_manager.load_from_dict(save_manager.player.npc_states)

    def capture_npc_states(self):
        self.player.npc_states = self.npc_manager.save_to_dict()

    def add_money(self, amount: int) -> int:
        self.player.money += amount
        return self.player.money

    def remove_money(self, amount: int) -> bool:
        if self.player.money >= amount:
            self.player.money -= amount
            return True
        return False

    def heal_team(self):
        if self.data_loader is None:
            raise RuntimeError("PlayerManager.heal_team requires data_loader")
        for pokemon in self.player.pokemon:
            profile = self.data_loader.get_pokemon(pokemon.name)
            max_hp = PokemonStat.max_hp(profile.stats.hp, pokemon.level)

            self.update_pokemon_hp(pokemon.name, max_hp)

            for move in pokemon.moves:
                move_profile = self.data_loader.get_move(move.name.lower())
                max_pp = move_profile.pp

                self.update_move_pp(pokemon.name, move.name, max_pp)

    def update_pokemon_hp(self, pokemon_name: str, hp: int):
        self.player.update_hp(pokemon_name, hp)

    def update_move_pp(self, pokemon_name: str, move_name: str, pp: int):
        self.player.update_move_pp(pokemon_name, move_name, pp)

    def update_pokemon_status(self, pokemon_name: str, status: str | None):
        self.player.update_status(pokemon_name, status)

    def update_level(
        self, pokemon_name: str, new_level: int, exp: int, evolved_name: str = None
    ):
        self.player.update_level(pokemon_name, new_level, exp, evolved_name)

    def learn_move(self, pokemon_name: str, move_name: str, index: int = None):
        move_data = self.data_loader.get_move(move_name)
        if not move_data:
            return

        move = PlayerPokemonMove(move_name, move_data.pp)

        if index:
            self.player.replace_move(pokemon_name, move, index)
        else:
            self.player.learn_move(pokemon_name, move)

    def persist_active_pokemon(
        self, battle_pokemon: BattlePokemon, has_evolved: bool
    ) -> None:
        """Write a battle Pokémon's hp/pp/level (and evolution) back to the save.
        Persistence lives here, not in BattleSystem (combat orchestration)."""
        name = battle_pokemon.name.lower()
        self.update_pokemon_hp(name, battle_pokemon.current_hp)
        # Persist the major status so it carries out of battle (and can be
        # cured with a bag item on the overworld). NONE -> None (healthy).
        status = battle_pokemon.status_effect
        self.update_pokemon_status(name, status.value if status.value else None)
        for move in battle_pokemon.moves:
            self.update_move_pp(name, move.name, move.pp)

        if not has_evolved:
            self.update_level(name, battle_pokemon.level, battle_pokemon.exp)
        else:
            self.update_level(
                name,
                battle_pokemon.level,
                battle_pokemon.exp,
                battle_pokemon.evolution.to,
            )

    def add_pokemon(self, pokemon: PlayerPokemon) -> bool:
        return self.player.add_pokemon(pokemon)

    def update_pokemon_held_item(self, pokemon_id: str, item_id: str | None):
        pokemon = self.get_pokemon(pokemon_id)
        pokemon.held_item = item_id

    def mark_seen(self, pokemon_name: str):
        self.player.mark_seen(pokemon_name)

    def add_item(self, item_id: str, count: int = 1):
        category = self.data_loader.get_item(item_id).category

        self.player.add_item(item_id, category, count)

    def consume_item(self, name: str) -> bool:
        return self.player.consume_item(name)

    def get_money(self) -> int:
        return self.player.money

    def get_pokemon(self, name: str) -> Optional[PlayerPokemon]:
        return self.player.get_pokemon(name)

    def get_pokemon_team(self) -> list[PlayerPokemon]:
        return self.player.pokemon

    def get_seen_pokemon(self) -> list[str]:
        return self.player.seen

    def get_inventory(self) -> list[ItemStack]:
        return self.player.items
