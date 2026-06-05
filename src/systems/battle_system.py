import random

from src.entities.pokemon_battle import PokemonBattle
from src.core.save_manager import SaveManager
from src.core.data_loader import DataLoader
from src.core.combat_calculator import calculate_damage
from src.core.event_bus import global_bus
from src.core.events import HpChangedEvent, PokemonFaintedEvent
from src.model.item import Item


class BattleSystem:
    def __init__(
        self,
        yourPokemon: PokemonBattle,
        enemyPokemon: PokemonBattle,
        save_manager: SaveManager,
        data_loader: DataLoader,
    ):
        self.yourPokemon = yourPokemon
        self.enemyPokemon = enemyPokemon
        self.save_manager = save_manager
        self.data_loader = data_loader

        self.turnQueue = []
        self.battleState = "intro"
        self.exp = 0
        self.hasEvolved = False

    def turn(self, moveIndex: int) -> list[str]:
        self.battleState = "currently turn"
        enemyMoveIndex = random.randint(0, len(self.enemyPokemon.moves) - 1)

        if self.yourPokemon.getStat("speed") >= self.enemyPokemon.getStat("speed"):
            self.turnQueue = [("player", moveIndex, -1), ("enemy", enemyMoveIndex, -1)]
        else:
            self.turnQueue = [("enemy", enemyMoveIndex, -1), ("player", moveIndex, -1)]

        return self.executeNextAction()

    def turnUseItem(self, itemIndex: int) -> list[str]:
        self.battleState = "currently turn"
        enemyMoveIndex = random.randint(0, len(self.enemyPokemon.moves) - 1)
        self.turnQueue = [("player", -1, itemIndex), ("enemy", enemyMoveIndex, -1)]
        return self.executeNextAction()
    
    def attemp_catch(self, pokeball:Item):
        effect = pokeball.effects[0]
        if effect.type == "catch":
            catchRate = 155
            catchChance = (3 * self.enemyPokemon.maxHp - 2 * self.enemyPokemon.currentHp) * catchRate * effect.catchRate // (3 * self.enemyPokemon.maxHp)

            if random.randint(1, 100) <= catchChance:
                return {"dialog": [f"You caught {self.enemyPokemon.name}!"], "caught": True}
            else:
                return {"dialog": [f"{self.enemyPokemon.name} broke free!"], "caught": False}

        return {"dialog": ["The pokeball had no effect!"], "caught": False}

    def executeNextAction(self) -> list[str]:
        if not self.turnQueue:
            return self.postTurn()

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
        attacker: PokemonBattle,
        defender: PokemonBattle,
        move_index: int,
        defender_label: str,
    ) -> list[str]:
        move_data = self.data_loader.getMove(attacker.moves[move_index].name)
        messages = []

        prefix = "" if attacker == self.yourPokemon else "Foe "
        messages.append(f"{prefix}{attacker.name} used {move_data.name}!")

        # Status / PP checks — PokemonBattle handles its own state
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
            crit_modifier=attacker.modifiers.get("crits", 0),
        )

        messages.extend(result.messages)

        # Apply damage
        hp_before = defender.currentHp
        if result.damage > 0:
            defender.takeDamage(result.damage)

        # Apply move effects (stat changes, status conditions) — state mutation
        effect_messages = attacker.executeEffects(move_data, defender)
        messages.extend(effect_messages)

        # Publish HP change for UI bar update
        self._publish_hp_change(defender_label, hp_before, defender)

        return messages

    def _applyItemToPokemon(self, itemIndex: int) -> list[str]:
        item = self.save_manager.player.items[itemIndex]
        self.yourPokemon.syncFromSource()

        global_bus.publish(
            HpChangedEvent(
                target="player",
                old_hp=self.yourPokemon.currentHp,
                new_hp=self.yourPokemon.currentHp,
                max_hp=self.yourPokemon.maxHp,
            )
        )

        return [f"{self.yourPokemon.name} used {item.name}!"]

    def postTurn(self) -> list[str]:
        messages = []
        hp_before_yours = self.yourPokemon.currentHp
        hp_before_enemy = self.enemyPokemon.currentHp

        messages.extend(self.yourPokemon.afterATurn())
        messages.extend(self.enemyPokemon.afterATurn())

        if self.yourPokemon.currentHp != hp_before_yours:
            self._publish_hp_change("player", hp_before_yours, self.yourPokemon)
        if self.enemyPokemon.currentHp != hp_before_enemy:
            self._publish_hp_change("enemy", hp_before_enemy, self.enemyPokemon)

        if self.yourPokemon.currentHp <= 0:
            messages.extend(self.pokemonDeath(self.yourPokemon))
            return messages
        if self.enemyPokemon.currentHp <= 0:
            messages.extend(self.pokemonDeath(self.enemyPokemon))
            return messages

        self.battleState = "post turn" if len(messages) > 0 else "waiting"
        return messages

    def pokemonDeath(self, diedPokemon: PokemonBattle) -> list[str]:
        messages = []
        self.battleState = "end"

        if diedPokemon.isEnemy:
            self.exp = diedPokemon.getExp()
            messages.extend(
                [
                    f"Wild {self.enemyPokemon.name} fainted!",
                    f"{self.yourPokemon.name} gained {self.exp} EXP. Points!",
                ]
            )
        else:
            messages.append(f"{self.yourPokemon.name} fainted!")

        global_bus.publish(
            PokemonFaintedEvent(
                target="enemy" if diedPokemon.isEnemy else "player",
                pokemon_name=diedPokemon.name,
            )
        )

        return messages

    def attempt_catch(self, item_data: Item) -> dict:
        ball_modifier = 1
        for effect in item_data.effects:
            if effect.type == "catch":
                ball_modifier = effect.catchRate or 1

        enemy = self.enemyPokemon
        pokemon_profile = self.data_loader.getPokemon(enemy.name.lower())
        catch_rate = pokemon_profile.catch_rate if pokemon_profile else 45

        hp_modifier = 1 - (enemy.currentHp / enemy.maxHp) * 0.5

        status_modifier = 1.0
        if enemy.statusEffect in ("sleep", "freeze"):
            status_modifier = 2.0
        elif enemy.statusEffect in ("paralyzed", "burned", "poisoned"):
            status_modifier = 1.5

        catch_probability = min(
            (catch_rate * ball_modifier * hp_modifier * status_modifier) / 255, 1.0
        )

        if random.random() < catch_probability:
            self.battleState = "caught"
            return {
                "success": True,
                "messages": [
                    f"You threw a Pokeball!",
                    f"Gotcha! {enemy.name} was caught!",
                ],
            }
        else:
            enemy_move_index = random.randint(0, len(self.enemyPokemon.moves) - 1)
            self.turnQueue = [("enemy", enemy_move_index, -1)]
            self.battleState = "currently turn"
            return {
                "success": False,
                "messages": [
                    f"You threw a Pokeball!",
                    f"Oh no! {enemy.name} broke free!",
                ],
            }

    def save(self):
        pokemonName = self.yourPokemon.name.lower()
        self.save_manager.updateHp(pokemonName, self.yourPokemon.currentHp)
        for move in self.yourPokemon.moves:
            self.save_manager.updateMove(pokemonName, move.name, move.pp)

        if not self.hasEvolved:
            self.save_manager.updateLevel(
                pokemonName, self.yourPokemon.level, self.yourPokemon.exp
            )
        else:
            self.save_manager.updateLevel(
                pokemonName,
                self.yourPokemon.level,
                self.yourPokemon.exp,
                self.yourPokemon.evolution.to,
            )

    def _publish_hp_change(self, target: str, hp_before: int, pokemon: PokemonBattle):
        global_bus.publish(
            HpChangedEvent(
                target=target,
                old_hp=hp_before,
                new_hp=pokemon.currentHp,
                max_hp=pokemon.maxHp,
            )
        )
