import random

from src.entities.battle_pokemon import BattlePokemon
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
        yourPokemon: BattlePokemon,
        enemyPokemon: BattlePokemon,
        player_manager: PlayerManager,
        data_loader: DataLoader,
        is_trainer=False,
        trainer_data: Optional[Trainer] = None,
    ):
        self.yourPokemon = yourPokemon
        self.enemyPokemon = enemyPokemon
        self.player_manager = player_manager
        self.data_loader = data_loader

        self.turnQueue = []
        self.battleState = BattleState.INTRO
        self.exp = 0
        self.hasEvolved = False

        self.is_trainer = is_trainer
        self.trainer_party = trainer_data.party if trainer_data else []
        self.next_trainer_pokemon: Optional[TrainerPokemon] = None

    def turn(self, moveIndex: int) -> list[str]:
        self.battleState = BattleState.CURRENTLY_TURN
        enemyMoveIndex = random.randint(0, len(self.enemyPokemon.moves) - 1)

        if self.yourPokemon.get_stat(Stat.SPEED) >= self.enemyPokemon.get_stat(Stat.SPEED):
            self.turnQueue = [("player", moveIndex, -1), ("enemy", enemyMoveIndex, -1)]
        else:
            self.turnQueue = [("enemy", enemyMoveIndex, -1), ("player", moveIndex, -1)]

        return self.execute_next_action()

    def turn_use_item(self, itemIndex: int) -> list[str]:
        self.battleState = BattleState.CURRENTLY_TURN
        enemyMoveIndex = random.randint(0, len(self.enemyPokemon.moves) - 1)
        self.turnQueue = [("player", -1, itemIndex), ("enemy", enemyMoveIndex, -1)]
        return self.execute_next_action()

    def switch_turn(self) -> list[str]:
        self.battleState = BattleState.CURRENTLY_TURN
        enemyMoveIndex = random.randint(0, len(self.enemyPokemon.moves) - 1)

        self.turnQueue = [("enemy", enemyMoveIndex, -1)]
        return self.execute_next_action()

    def switch_pokemon(self) -> list[str]:
        pokemon = self.player_manager.player.pokemon[0]
        pokemonProfile = self.data_loader.get_pokemon(pokemon.name)

        if pokemon.hp <= 0:
            return [f"{pokemon.name} is unable to battle!"]

        self.yourPokemon.switching_pokemon(pokemon, pokemonProfile)

        return [f"Go {pokemon.name}!"]

    def execute_next_action(self) -> list[str]:
        if not self.turnQueue:
            return self.post_turn()

        messages = []
        attackerKey, moveIndex, itemIndex = self.turnQueue.pop(0)

        if attackerKey == "player" and self.yourPokemon.currentHp > 0:
            if itemIndex == -1:
                messages.extend(
                    self._execute_move(
                        self.yourPokemon, self.enemyPokemon, moveIndex, "enemy"
                    )
                )
            else:
                messages.extend(self._applyItemToPokemon(itemIndex))

        elif attackerKey == "enemy" and self.enemyPokemon.currentHp > 0:
            messages.extend(
                self._execute_move(
                    self.enemyPokemon, self.yourPokemon, moveIndex, "player"
                )
            )

        if self.yourPokemon.currentHp <= 0 or self.enemyPokemon.currentHp <= 0:
            self.turnQueue.clear()

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

        prefix = "" if attacker == self.yourPokemon else "Foe "
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
            attacker_status=attacker.statusEffect,
            move_data=move_data,
            defender_stats=defender.stats,
            defender_types=defender.types,
            defender_modifiers=defender.modifiers,
            crit_modifier=attacker.modifiers.get(Stat.CRITS, 0),
        )

        messages.extend(result.messages)

        # Apply damage
        hp_before = defender.currentHp
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

    def _applyItemToPokemon(self, itemIndex: int) -> list[str]:
        item = self.player_manager.player.items[itemIndex]
        self.yourPokemon.sync_from_source()

        global_bus.publish(
            HpChangedEvent(
                target="player",
                old_hp=self.yourPokemon.currentHp,
                new_hp=self.yourPokemon.currentHp,
                max_hp=self.yourPokemon.maxHp,
            )
        )

        return [f"{self.yourPokemon.name} used {item.name}!"]

    def post_turn(self) -> list[str]:
        messages = []
        hp_before_yours = self.yourPokemon.currentHp
        hp_before_enemy = self.enemyPokemon.currentHp

        messages.extend(self.yourPokemon.after_a_turn())
        messages.extend(self.enemyPokemon.after_a_turn())

        if self.yourPokemon.currentHp != hp_before_yours:
            self._publish_hp_change("player", hp_before_yours, self.yourPokemon)
        if self.enemyPokemon.currentHp != hp_before_enemy:
            self._publish_hp_change("enemy", hp_before_enemy, self.enemyPokemon)

        if self.yourPokemon.currentHp <= 0:
            messages.extend(self.pokemon_death(self.yourPokemon))
            return messages
        if self.enemyPokemon.currentHp <= 0:
            messages.extend(self.pokemon_death(self.enemyPokemon))
            return messages

        self.battleState = BattleState.POST_TURN if len(messages) > 0 else BattleState.WAITING
        return messages

    def pokemon_death(self, diedPokemon: BattlePokemon) -> list[str]:
        messages = []

        if diedPokemon.isEnemy:
            self.battleState = BattleState.END
            self.exp = diedPokemon.exp_yield()
            messages.extend(
                [
                    f"{self.enemyPokemon.name} fainted!",
                    f"{self.yourPokemon.name} gained {self.exp} EXP. Points!",
                ]
            )

            if self.is_trainer and self.trainer_party:
                self.next_trainer_pokemon = self.trainer_party.pop(0)
                self.battleState = BattleState.TRAINER_SWITCH
        else:
            # Persist the faint to the team member (through the single mutation
            # door, not a raw save-layer write) so the bench/active HP is accurate
            # when we decide between switching and losing. save() only persists the
            # active pokemon, so a fainted-then-switched-out mon must be saved here.
            if self.yourPokemon.source is not None:
                self.player_manager.update_pokemon_hp(
                    self.yourPokemon.name.lower(), self.yourPokemon.currentHp
                )
            self.battleState = BattleState.PLAYER_FAINTED
            messages.append(f"{self.yourPokemon.name} fainted!")

        global_bus.publish(
            PokemonFaintedEvent(
                target="enemy" if diedPokemon.isEnemy else "player",
                pokemon_name=diedPokemon.name,
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
        self.yourPokemon.switching_pokemon(pokemon, profile)
        return [f"Go {pokemon.name}!"]

    def attempt_catch(self, item_data: ItemSpecies) -> dict:
        ball_modifier = 1
        for effect in item_data.effects:
            if effect.type == EffectType.CATCH:
                ball_modifier = effect.catch_rate or 1

        enemy = self.enemyPokemon
        pokemon_profile = self.data_loader.get_pokemon(enemy.name.lower())
        catch_rate = pokemon_profile.catch_rate if pokemon_profile else 45

        hp_modifier = 1 - (enemy.currentHp / enemy.maxHp) * 0.5

        status_modifier = 1.0
        if enemy.statusEffect in (StatusEffect.SLEEP, StatusEffect.FREEZE):
            status_modifier = 2.0
        elif enemy.statusEffect in (
            StatusEffect.PARALYSIS,
            StatusEffect.BURN,
            StatusEffect.POISON,
        ):
            status_modifier = 1.5

        catch_probability = min(
            (catch_rate * ball_modifier * hp_modifier * status_modifier) / 255, 1.0
        )

        if random.random() < catch_probability:
            self.battleState = BattleState.CAUGHT
            return {
                "success": True,
                "messages": [
                    "You threw a Pokeball!",
                    f"Gotcha! {enemy.name} was caught!",
                ],
            }
        else:
            enemy_move_index = random.randint(0, len(self.enemyPokemon.moves) - 1)
            self.turnQueue = [("enemy", enemy_move_index, -1)]
            self.battleState = BattleState.CURRENTLY_TURN
            return {
                "success": False,
                "messages": [
                    "You threw a Pokeball!",
                    f"Oh no! {enemy.name} broke free!",
                ],
            }

    def save(self):
        pokemonName = self.yourPokemon.name.lower()
        self.player_manager.update_pokemon_hp(pokemonName, self.yourPokemon.currentHp)
        for move in self.yourPokemon.moves:
            self.player_manager.update_move_pp(pokemonName, move.name, move.pp)

        if not self.hasEvolved:
            self.player_manager.update_level(
                pokemonName, self.yourPokemon.level, self.yourPokemon.exp
            )
        else:
            self.player_manager.update_level(
                pokemonName,
                self.yourPokemon.level,
                self.yourPokemon.exp,
                self.yourPokemon.evolution.to,
            )

    def _publish_hp_change(self, target: str, hp_before: int, pokemon: BattlePokemon):
        global_bus.publish(
            HpChangedEvent(
                target=target,
                old_hp=hp_before,
                new_hp=pokemon.currentHp,
                max_hp=pokemon.maxHp,
            )
        )
