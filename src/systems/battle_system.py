import random

from src.model.battle.battle_pokemon import BattlePokemon
from src.core.player_manager import PlayerManager
from src.core.data_loader import DataLoader
from src.core.combat_calculator import calculate_damage
from src.core.catch_calculator import calc_catch_probability
from src.core.event_bus import global_bus
from src.core.events import HpChangedEvent, PokemonFaintedEvent
from src.enums.battle_state import BattleState
from src.enums.stat import Stat
from src.enums.effect_type import EffectType
from src.model.battle.exp_gain_result import ExpGainResult
from src.model.save.player import PlayerPokemon
from src.model.static.item import ItemSpecies
from src.model.static.trainer import Trainer, TrainerPokemon
from src.model.static.pokemon import PokemonMove
from typing import Optional
from src.systems.enemy_ai import EnemyAI


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
        
        self._last_player_move = ""
        
        self.ai = EnemyAI(1, data_loader)

        self.is_trainer = is_trainer
        self.trainer_party = trainer_data.party if trainer_data else []
        self.next_trainer_pokemon: Optional[TrainerPokemon] = None

    def turn(self, move_index: int) -> list[str]:
        self.battle_state = BattleState.CURRENTLY_TURN
        enemy_move_index = self.ai.select_move(self.enemy_pokemon, self.your_pokemon)
    
        player_priority = self.data_loader.get_move(self.your_pokemon.moves[move_index].name).priority
        enemy_priority = self.data_loader.get_move(self.enemy_pokemon.moves[enemy_move_index].name).priority

        if self._player_moves_first(self.your_pokemon.get_stat(Stat.SPEED), player_priority, self.enemy_pokemon.get_stat(Stat.SPEED), enemy_priority):
            self.turn_queue = [("player", move_index, -1), ("enemy", enemy_move_index, -1)]
        else:
            self.turn_queue = [("enemy", enemy_move_index, -1), ("player", move_index, -1)]

        return self.execute_next_action()
    
    def _player_moves_first(self, player_speed: int, player_priority: int, enemy_speed: int, enemy_priority: int) -> bool:
        return player_priority > enemy_priority or (
            player_priority == enemy_priority and player_speed >= enemy_speed
        )

    def turn_use_item(self, item_index: int) -> list[str]:
        self.battle_state = BattleState.CURRENTLY_TURN
        enemy_move_index = self.ai.select_move(self.enemy_pokemon, self.your_pokemon)
        self.turn_queue = [("player", -1, item_index), ("enemy", enemy_move_index, -1)]
        return self.execute_next_action()

    def switch_turn(self) -> list[str]:
        self.battle_state = BattleState.CURRENTLY_TURN
        enemy_move_index = self.ai.select_move(self.enemy_pokemon, self.your_pokemon)

        self.turn_queue = [("enemy", enemy_move_index, -1)]
        return self.execute_next_action()

    def switch_pokemon(self) -> list[str]:
        pokemon = self.player_manager.player.pokemon[0]
        pokemon_profile = self.data_loader.get_pokemon(pokemon.name)
        ability = self.data_loader.get_ability(pokemon.ability)

        if pokemon.hp <= 0:
            return [f"{pokemon.name} is unable to battle!"]
        
        messages = [f"Go {pokemon.name}!"]

        self.your_pokemon.switching_pokemon(pokemon, ability, pokemon_profile)

        messages.extend(self.your_pokemon.on_switch_in(self.enemy_pokemon))
        return messages

    def execute_next_action(self) -> list[str]:
        if not self.turn_queue:
            return self.post_turn()

        messages = []
        attacker_key, move_index, item_index = self.turn_queue.pop(0)

        if attacker_key == "player" and self.your_pokemon.current_hp > 0:
            if item_index == -1:
                messages.extend(
                    self._dispatch_move(
                        self.your_pokemon, self.enemy_pokemon, move_index, "enemy"
                    )
                )
            else:
                messages.extend(self._apply_item_to_pokemon(item_index))

        elif attacker_key == "enemy" and self.enemy_pokemon.current_hp > 0:
            messages.extend(
                self._dispatch_move(
                    self.enemy_pokemon, self.your_pokemon, move_index, "player"
                )
            )

        if self.your_pokemon.current_hp <= 0 or self.enemy_pokemon.current_hp <= 0:
            self.turn_queue.clear()

        return messages
    
    def _dispatch_move(
        self,
        attacker: BattlePokemon,
        defender: BattlePokemon,
        move_index: int,
        defender_label: str,
    ) -> list[str]:
        """Routes to single-hit or multi-hit execution based on move data."""
        move_data = self.data_loader.get_move(attacker.moves[move_index].name)

        if move_data.multi_hit:
            return self._execute_move_multiple_times(
                attacker, defender, move_index, defender_label
            )
        return self._execute_move(attacker, defender, move_index, defender_label)

    def _execute_move_multiple_times(
        self,
        attacker: BattlePokemon,
        defender: BattlePokemon,
        move_index: int,
        defender_label: str
    ) -> list[str]:
        move_data = self.data_loader.get_move(attacker.moves[move_index].name)
        min_hits, max_hits = move_data.multi_hit
        times = random.randint(min_hits, max_hits)

        messages = []
        hits_landed = 0

        for hit_number in range(1, times + 1):
            hit_messages = self._execute_move(
                attacker, defender, move_index, defender_label,
                announce=(hit_number == 1),
            )
            messages.extend(hit_messages)
            hits_landed += 1

            if defender.current_hp <= 0:
                break
        if hits_landed > 1:
            messages.append(f"Hit {hits_landed} time(s)!")

        return messages

    def _execute_move(
        self,
        attacker: BattlePokemon,
        defender: BattlePokemon,
        move_index: int,
        defender_label: str,
        announce:bool = True
    ) -> list[str]:
        move_data = self.data_loader.get_move(attacker.moves[move_index].name)
        messages = []

        if announce:
            prefix = "" if attacker == self.your_pokemon else "Foe "
            messages.append(f"{prefix}{attacker.name} used {move_data.name}!")

            # Status / PP checks
            status_messages, can_move = attacker.check_can_move(move_index)
            messages.extend(status_messages)
            if not can_move:
                return messages
            
            failure_message = self._check_move_condition(move_data, attacker)
            if failure_message:
                messages.append(failure_message)
                return messages

        if defender.is_protected:
            messages.append(f"{defender.name} protected itself!")
            return messages

        # Ability: defender immunity (e.g. Levitate vs Ground) — absolute, so
        # short-circuit before accuracy/damage are even rolled.
        immunity_message = defender.immunity_to(move_data)
        if immunity_message:
            messages.append(immunity_message)
            return messages

        # Ability: attacker on-attack power boost (e.g. Blaze at low HP).
        attack_multiplier, ability_attack_messages = attacker.ability_attack_multiplier(
            move_data
        )

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
            crit_modifier=attacker.modifiers.get(Stat.CRITS, 0) + move_data.crit,
            type_chart=self.data_loader.types,
        )

        messages.extend(result.messages)

        if result.is_miss:
            return messages

        # Apply damage (with any attacker-ability multiplier)
        damage = round(result.damage * attack_multiplier)
        hp_before = defender.current_hp
        if damage > 0:
            defender.take_damage(damage)
            messages.extend(ability_attack_messages)

        # Apply move effects (stat changes, status conditions) — state mutation
        effect_messages = attacker.execute_effects(move_data, defender)
        messages.extend(effect_messages)

        # Ability: defender on-hit reaction (e.g. Static paralyses on contact)
        messages.extend(defender.on_hit(attacker, move_data))

        # Publish HP change for UI bar update
        self._publish_hp_change(defender_label, hp_before, defender)

        self._last_player_move = move_data.name

        return messages
    
    def _check_move_condition(self, move_data:PokemonMove, attacker:BattlePokemon) -> str | None:
        """Returns a failure message if the move's condition isn't met, else None."""
        condition = move_data.condition
        if not condition:
            return None

        if condition == "first_turn_only":
            if not attacker.is_first_turn:   
                return f"But {move_data.name} failed!"

        if condition == "not_consecutive":
            if self._last_player_move == move_data.name:
                return f"But {move_data.name} failed!"

        return None

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
        
        messages.extend(self.your_pokemon.on_turn_end(self.enemy_pokemon))
        messages.extend(self.enemy_pokemon.on_turn_end(self.your_pokemon))

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
        messages = []
         
        pokemon = self.player_manager.player.pokemon[0]
        profile = self.data_loader.get_pokemon(pokemon.name)
        ability = self.data_loader.get_ability(pokemon.ability)
        self.your_pokemon.switching_pokemon(pokemon, ability, profile)
        
        messages.extend(self.your_pokemon.on_switch_in(self.enemy_pokemon))
        messages.append(f"Go {pokemon.name}!")
        
        return messages
    
    def apply_exp_award(self) -> ExpGainResult:
        """Award pending exp to the active Pokémon and clear it. Returns the
        ExpGainResult so the view can react (level-up / evolve / nothing)
        without mutating the model itself."""
        result = self.your_pokemon.gain_exp(self.exp)
        self.exp = 0
        return result

    def add_caught_pokemon(self) -> None:
        """Add the just-caught enemy to the party (CAUGHT flow)."""
        enemy = self.enemy_pokemon
        self.player_manager.add_pokemon(
            PlayerPokemon(
                name=enemy.name.lower(),
                hp=enemy.current_hp,
                level=enemy.level,
                exp=0,
                moves=enemy.moves,
                ability=enemy.ability.name.lower()
            )
        )

    def attempt_catch(self, item_data: ItemSpecies) -> dict:
        ball_modifier = 1
        for effect in item_data.effects:
            if effect.type == EffectType.CATCH:
                ball_modifier = effect.catch_rate or 1

        enemy = self.enemy_pokemon
        pokemon_profile = self.data_loader.get_pokemon(enemy.name.lower())
        catch_rate = pokemon_profile.catch_rate if pokemon_profile else 45

        catch_probability = calc_catch_probability(
            catch_rate,
            ball_modifier,
            enemy.current_hp,
            enemy.max_hp,
            enemy.status_effect,
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
        # Persistence is owned by the PlayerManager Facade, not combat code.
        self.player_manager.persist_active_pokemon(self.your_pokemon, self.has_evolved)

    def _publish_hp_change(self, target: str, hp_before: int, pokemon: BattlePokemon):
        global_bus.publish(
            HpChangedEvent(
                target=target,
                old_hp=hp_before,
                new_hp=pokemon.current_hp,
                max_hp=pokemon.max_hp,
            )
        )
