import arcade
from src.entities.pokemonBattle import PokemonBattle
from src.core.bagSystem import BagSystem
from src.core.gameContext import saveManager, dataLoader
import random


class BattleSystem:
    def __init__(self, yourPokemon: PokemonBattle, enemyPokemon: PokemonBattle):
        self.yourPokemon = yourPokemon
        self.enemyPokemon = enemyPokemon
        self.bag = BagSystem()

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

    def executeNextAction(self) -> list[str]:
        if not self.turnQueue:
            return self.postTurn()

        messages = []

        attackerKey, moveIndex, itemIndex = self.turnQueue.pop(0)

        if attackerKey == "player" and self.yourPokemon.currentHp > 0:
            result = []
            if itemIndex == -1:
                moveName = self.yourPokemon.moves[moveIndex].name
                messages.append(f"{self.yourPokemon.name} used {moveName}!")
                result = self.yourPokemon.useMove(moveIndex, self.enemyPokemon)
            else:
                itemName = self.bag.getItems()[itemIndex].name
                self.bag.useItem(itemIndex, self.yourPokemon.name)
                result = [f"{self.yourPokemon.name} used {itemName}!"]
                
            messages.extend(result)
        elif attackerKey == "enemy" and self.enemyPokemon.currentHp > 0:
            moveName = self.enemyPokemon.moves[moveIndex].name
            messages.append(f"Foe {self.enemyPokemon.name} used {moveName}!")
            result = self.enemyPokemon.useMove(moveIndex, self.yourPokemon)
            messages.extend(result)

        return messages

    def pokemonDeath(self, diedPokemon: PokemonBattle) -> list[str]:
        message = []
        self.battleState = "end"
        if diedPokemon.isEnemy:
            self.exp = diedPokemon.getExp()

            message.extend(
                [
                    f"Wild {self.enemyPokemon.name} fainted!",
                    f"{self.yourPokemon.name} gained {self.exp} EXP. Points!",
                ]
            )
        else:
            self.ui.messageQueue.extend([f"{self.yourPokemon.name} fainted!"])

        return message

    def postTurn(self) -> list[str]:
        messages = []

        messages.extend(self.yourPokemon.afterATurn())
        messages.extend(self.enemyPokemon.afterATurn())

        if self.yourPokemon.currentHp <= 0:
            messages.extend(self.pokemonDeath(self.yourPokemon))
            return messages

        if self.enemyPokemon.currentHp <= 0:
            messages.extend(self.pokemonDeath(self.enemyPokemon))
            return messages

        if len(messages) - 1 > 0:
            self.battleState = "post turn"
        else:
            self.battleState = "waiting"

        return messages

    def save(self):
        saveManager.updateHp(self.yourPokemon.name, self.yourPokemon.currentHp)
        for move in self.yourPokemon.moves:
            saveManager.updateMove(self.yourPokemon.name, move.name, move.pp)

        if not self.hasEvolved:
            saveManager.updateLevel(
                self.yourPokemon.name, self.yourPokemon.level, self.yourPokemon.exp
            )
        else:
            saveManager.updateLevel(
                self.yourPokemon.name,
                self.yourPokemon.level,
                self.yourPokemon.exp,
                self.yourPokemon.evolution.to,
            )
