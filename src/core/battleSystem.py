import arcade
from src.entities.pokemonBattle import PokemonBattle
from src.core.gameContext import saveManager
import random

class BattleSystem:
    def __init__(self, yourPokemon: PokemonBattle, enemyPokemon:PokemonBattle):
        self.yourPokemon = yourPokemon
        self.enemyPokemon = enemyPokemon
        
        self.turnQueue = []
        self.battleState = "intro"
        self.exp = 0
        self.hasEvolved = False
        
    def turn(self, moveIndex) -> list[str]:
        self.battleState = "currently turn"

        enemyMoveIndex = random.randint(0, len(self.enemyPokemon.moves) - 1)

        if self.yourPokemon.getStat("speed") >= self.enemyPokemon.getStat("speed"):
            self.turnQueue = [("player", moveIndex),
                               ("enemy", enemyMoveIndex)]
        else:
            self.turnQueue = [("enemy", enemyMoveIndex),
                               ("player", moveIndex)]

        return self.executeNextAction()

    def executeNextAction(self) -> list[str]:
        if not self.turnQueue:
            return self.postTurn()

        messages = []

        attackerKey, moveIndex = self.turnQueue.pop(0)

        if attackerKey == "player" and self.yourPokemon.currentHp > 0:
            moveName = self.yourPokemon.moves[moveIndex].name
            messages.append(f"{self.yourPokemon.name} used {moveName}!")
            result = self.yourPokemon.useMove(moveIndex, self.enemyPokemon)
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
            self.ui.messageQueue.extend(
                [f"{self.yourPokemon.name} fainted!"])

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

