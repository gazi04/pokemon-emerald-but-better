import random

from src.model.battle.battle_pokemon import BattlePokemon
from src.core.player_manager import PlayerManager
from src.core.data_loader import DataLoader
from src.core.combat_calculator import calculate_damage
from src.core.event_bus import global_bus
from src.core.events import HpChangedEvent, PokemonFaintedEvent
from src.model.battle.battle_state import BattleState
from src.model.battle.stat import Stat
from src.model.battle.status_effect import StatusEffect
from src.model.battle.effect_type import EffectType
from src.model.static.item import ItemSpecies
from src.model.static.trainer import Trainer, TrainerPokemon
from typing import Optional


class BattleSystem:
    def __init__(
        self,
        your_pokemon: BattlePokemon,
        enemy_pokemon: BattlePokemon,
        player_manager: PlayerManager,
        data_loader: DataLoader,
        is_trainer=False,
        trainer_data: Optional[Trainer] = None,
    ):
        self.your_pokemon = your_pokemon
        self.enemy_pokemon = enemy_pokemon
        self.player_manager = player_manager
        self.data_loader = data_loader

        self.turn_queue = []
        self.battle_state = BattleState.INTRO
        self.exp = 0
        self.has_evolved = False

        self.is_trainer = is_trainer
        self.trainer_party = trainer_data.party if trainer_data else []
        self.next_trainer_pokemon: Optional[TrainerPokemon] = None

    def turn(self, move_index: int) -> list[str]:
        self.battle_state = BattleState.CURRENTLY_TURN
        enemy_move_index = random.randint(0, len(self.enemy_pokemon.moves) - 1)

        if self.your_pokemon.get_stat(Stat.SPEED) >= self.enemy_pokemon.get_stat(Stat.SPEED):
            self.turn_queue = [("player", move_index, -1), ("enemy", enemy_move_index, -1)]
        else:
            self.turn_queue = [("enemy", enemy_move_index, -1), ("player", move_index, -1)]

        return self.execute_next_action()

    def turn_use_item(self, item_index: int) -> list[str]:
        self.battle_state = BattleState.CURRENTLY_TURN
        enemy_move_index = random.randint(0, len(self.enemy_pokemon.moves) - 1)
        self.turn_queue = [("player", -1, item_index), ("enemy", enemy_move_index, -1)]
        return self.execute_next_action()

    def switch_turn(self) -> list[str]:
        self.battle_state = BattleState.CURRENTLY_TURN
        enemy_move_index = random.randint(0, len(self.enemy_pokemon.moves) - 1)

        self.turn_queue = [("enemy", enemy_move_index, -1)]
        return self.execute_next_action()

    def switch_pokemon(self) -> list[str]:
        pokemon = self.player_manager.player.pokemon[0]
        pokemon_profile = self.data_loader.get_pokemon(pokemon.name)

        if pokemon.hp <= 0:
            return [f"{pokemon.name} is unable to battle!"]

        self.your_pokemon.switching_pokemon(pokemon, pokemon_profile)

        return [f"Go {pokemon.name}!"]

    def execute_next_action(self) -> list[str]:
        if not self.turn_queue:
            return self.post_turn()

        messages = []
        attacker_key, move_index, item_index = self.turn_queue.pop(0)

        if attacker_key == "player" and self.your_pokemon.current_hp > 0:
            if item_index == -1:
                messages.extend(
                    self._execute_move(
                        self.your_pokemon, self.enemy_pokemon, move_index, "enemy"
                    )
                )
            else:
                messages.extend(self._apply_item_to_pokemon(item_index))

        elif attacker_key == "enemy" and self.enemy_pokemon.current_hp > 0:
            messages.extend(
                self._execute_move(
                    self.enemy_pokemon, self.your_pokemon, move_index, "player"
                )
            )

        if self.your_pokemon.current_hp <= 0 or self.enemy_pokemon.current_hp <= 0:
            self.turn_queue.clear()

        return messages

    def _execute_move(
        self,
        attacker: BattlePokemon,
        defender: BattlePokemon,
        move_index: int,
        defender_label: str,
    ) -> list[str]:
        move_data = self.data_loader.get_move(attacker.moves[move_index].name)
        messages = []

        prefix = "" if attacker == self.your_pokemon else "Foe "
        messages.append(f"{prefix}{attacker.name} used {move_data.name}!")

        # Status / PP checks — BattlePokemon handles its own state
        status_messages, can_move = attacker.check_can_move(move_index)
        messages.extend(status_messages)
        if not can_move:
            return messages

        # Pure damage calculation — no side effects
        result = calculate_damage(
            attacker_level=attacker.level,
            attacker_stats=attacker.stats,
            attacker_types=attacker.types,
            attacker_modifiers=attacker.modifiers,
            attacker_status=attacker.status_effect,
            move_data=move_data,
            defender_stats=defender.stats,
            defender_types=defender.types,
            defender_modifiers=defender.modifiers,
            crit_modifier=attacker.modifiers.get(Stat.CRITS, 0),
        )

        messages.extend(result.messages)

        # Apply damage
        hp_before = defender.current_hp
        if result.damage > 0:
            defender.take_damage(result.damage)

        if result.is_miss:
            return messages

        # Apply move effects (stat changes, status conditions) — state mutation
        effect_messages = attacker.execute_effects(move_data, defender)
        messages.extend(effect_messages)

        # Publish HP change for UI bar update
        self._publish_hp_change(defender_label, hp_before, defender)

        return messages

    def _apply_item_to_pokemon(self, item_index: int) -> list[str]:
        item = self.player_manager.player.items[item_index]
        self.your_pokemon.sync_from_source()

        global_bus.publish(
            HpChangedEvent(
                target="player",
                old_hp=self.your_pokemon.current_hp,
                new_hp=self.your_pokemon.current_hp,
                max_hp=self.your_pokemon.max_hp,
            )
        )

        return [f"{self.your_pokemon.name} used {item.name}!"]

    def post_turn(self) -> list[str]:
        messages = []
        hp_before_yours = self.your_pokemon.current_hp
        hp_before_enemy = self.enemy_pokemon.current_hp

        messages.extend(self.your_pokemon.after_a_turn())
        messages.extend(self.enemy_pokemon.after_a_turn())

        if self.your_pokemon.current_hp != hp_before_yours:
            self._publish_hp_change("player", hp_before_yours, self.your_pokemon)
        if self.enemy_pokemon.current_hp != hp_before_enemy:
            self._publish_hp_change("enemy", hp_before_enemy, self.enemy_pokemon)

        if self.your_pokemon.current_hp <= 0:
            messages.extend(self.pokemon_death(self.your_pokemon))
            return messages
        if self.enemy_pokemon.current_hp <= 0:
            messages.extend(self.pokemon_death(self.enemy_pokemon))
            return messages

        self.battle_state = BattleState.POST_TURN if len(messages) > 0 else BattleState.WAITING
        return messages

    def pokemon_death(self, died_pokemon: BattlePokemon) -> list[str]:
        messages = []

        if died_pokemon.is_enemy:
            self.battle_state = BattleState.END
            self.exp = died_pokemon.exp_yield()
            messages.extend(
                [
                    f"{self.enemy_pokemon.name} fainted!",
                    f"{self.your_pokemon.name} gained {self.exp} EXP. Points!",
                ]
            )

            if self.is_trainer and self.trainer_party:
                self.next_trainer_pokemon = self.trainer_party.pop(0)
                self.battle_state = BattleState.TRAINER_SWITCH
        else:
            # Persist the faint to the team member (through the single mutation
            # door, not a raw save-layer write) so the bench/active HP is accurate
            # when we decide between switching and losing. save() only persists the
            # active pokemon, so a fainted-then-switched-out mon must be saved here.
            if self.your_pokemon.source is not None:
                self.player_manager.update_pokemon_hp(
                    self.your_pokemon.name.lower(), self.your_pokemon.current_hp
                )
            self.battle_state = BattleState.PLAYER_FAINTED
            messages.append(f"{self.your_pokemon.name} fainted!")

        global_bus.publish(
            PokemonFaintedEvent(
                target="enemy" if died_pokemon.is_enemy else "player",
                pokemon_name=died_pokemon.name,
            )
        )

        return messages

    def has_usable_pokemon(self) -> bool:
        """True if the player still has at least one Pokémon that can fight."""
        return any(p.hp > 0 for p in self.player_manager.player.pokemon)

    def complete_forced_switch(self) -> list[str]:
        """
        Bring in the replacement chosen after a faint. The team list has
        already been reordered so the new active is at index 0. No enemy turn
        follows a forced switch.
        """
        pokemon = self.player_manager.player.pokemon[0]
        profile = self.data_loader.get_pokemon(pokemon.name)
        self.your_pokemon.switching_pokemon(pokemon, profile)
        return [f"Go {pokemon.name}!"]

    def attempt_catch(self, item_data: ItemSpecies) -> dict:
        ball_modifier = 1
        for effect in item_data.effects:
            if effect.type == EffectType.CATCH:
                ball_modifier = effect.catch_rate or 1

        enemy = self.enemy_pokemon
        pokemon_profile = self.data_loader.get_pokemon(enemy.name.lower())
        catch_rate = pokemon_profile.catch_rate if pokemon_profile else 45

        hp_modifier = 1 - (enemy.current_hp / enemy.max_hp) * 0.5

        status_modifier = 1.0
        if enemy.status_effect in (StatusEffect.SLEEP, StatusEffect.FREEZE):
            status_modifier = 2.0
        elif enemy.status_effect in (
            StatusEffect.PARALYSIS,
            StatusEffect.BURN,
            StatusEffect.POISON,
        ):
            status_modifier = 1.5

        catch_probability = min(
            (catch_rate * ball_modifier * hp_modifier * status_modifier) / 255, 1.0
        )

        if random.random() < catch_probability:
            self.battle_state = BattleState.CAUGHT
            return {
                "success": True,
                "messages": [
                    "You threw a Pokeball!",
                    f"Gotcha! {enemy.name} was caught!",
                ],
            }
        else:
            enemy_move_index = random.randint(0, len(self.enemy_pokemon.moves) - 1)
            self.turn_queue = [("enemy", enemy_move_index, -1)]
            self.battle_state = BattleState.CURRENTLY_TURN
            return {
                "success": False,
                "messages": [
                    "You threw a Pokeball!",
                    f"Oh no! {enemy.name} broke free!",
                ],
            }

    def save(self):
        pokemon_name = self.your_pokemon.name.lower()
        self.player_manager.update_pokemon_hp(pokemon_name, self.your_pokemon.current_hp)
        for move in self.your_pokemon.moves:
            self.player_manager.update_move_pp(pokemon_name, move.name, move.pp)

        if not self.has_evolved:
            self.player_manager.update_level(
                pokemon_name, self.your_pokemon.level, self.your_pokemon.exp
            )
        else:
            self.player_manager.update_level(
                pokemon_name,
                self.your_pokemon.level,
                self.your_pokemon.exp,
                self.your_pokemon.evolution.to,
            )

    def _publish_hp_change(self, target: str, hp_before: int, pokemon: BattlePokemon):
        global_bus.publish(
            HpChangedEvent(
                target=target,
                old_hp=hp_before,
                new_hp=pokemon.current_hp,
                max_hp=pokemon.max_hp,
            )
        )
