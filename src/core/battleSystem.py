import random

from src.core.dataLoader import DataLoader
from src.core.saveManager import SaveManager
from src.entities.pokemonBattle import PokemonBattle
from src.core.gameContext import saveManager
from src.core.event_bus import global_bus
from src.core.events import HpChangedEvent, PokemonFaintedEvent


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

    def turn(self, moveIndex) -> list[str]:
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

    def executeNextAction(self) -> list[str]:
        if not self.turnQueue:
            return self.postTurn()

        messages = []
        attackerKey, moveIndex, itemIndex = self.turnQueue.pop(0)

        if attackerKey == "player" and self.yourPokemon.currentHp > 0:
            if itemIndex == -1:
                moveName = self.yourPokemon.moves[moveIndex].name
                # Phase 4: fetch move here, pass data into useMove
                move_data = self.data_loader.getMove(moveName)
                messages.append(f"{self.yourPokemon.name} used {moveName}!")
                hp_before = self.enemyPokemon.currentHp
                result = self.yourPokemon.useMove(
                    move_data, moveIndex, self.enemyPokemon
                )
                self._publish_hp_change("enemy", hp_before, self.enemyPokemon)
                messages.extend(result)
            else:
                messages.extend(self._applyItemToPokemon(itemIndex))

        elif attackerKey == "enemy" and self.enemyPokemon.currentHp > 0:
            moveName = self.enemyPokemon.moves[moveIndex].name
            move_data = self.data_loader.getMove(moveName)
            messages.append(f"Foe {self.enemyPokemon.name} used {moveName}!")
            hp_before = self.yourPokemon.currentHp
            result = self.enemyPokemon.useMove(move_data, moveIndex, self.yourPokemon)
            self._publish_hp_change("player", hp_before, self.yourPokemon)
            messages.extend(result)

        if self.yourPokemon.currentHp <= 0 or self.enemyPokemon.currentHp <= 0:
            self.turnQueue.clear()

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

        # Death check — covers both mid-turn kills and post-turn poison kills
        if self.yourPokemon.currentHp <= 0:
            messages.extend(self.pokemonDeath(self.yourPokemon))
            return messages

        if self.enemyPokemon.currentHp <= 0:
            messages.extend(self.pokemonDeath(self.enemyPokemon))
            return messages

        if len(messages) > 0:
            self.battleState = "post turn"
        else:
            self.battleState = "waiting"

        return messages

    def save(self):
        self.save_manager.updateHp(self.yourPokemon.name, self.yourPokemon.currentHp)
        for move in self.yourPokemon.moves:
            self.save_manager.updateMove(self.yourPokemon.name, move.name, move.pp)

        if not self.hasEvolved:
            self.save_manager.updateLevel(
                self.yourPokemon.name, self.yourPokemon.level, self.yourPokemon.exp
            )
        else:
            self.save_manager.updateLevel(
                self.yourPokemon.name,
                self.yourPokemon.level,
                self.yourPokemon.exp,
                self.yourPokemon.evolution.to,
            )

    def _publish_hp_change(self, target: str, hp_before: int, pokemon: PokemonBattle):
        # Only publishes the HP change for UI updates — death is handled by postTurn
        global_bus.publish(
            HpChangedEvent(
                target=target,
                old_hp=hp_before,
                new_hp=pokemon.currentHp,
                max_hp=pokemon.maxHp,
            )
        )
