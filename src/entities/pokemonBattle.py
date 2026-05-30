from src.util import calculateMultiplier
import random
from src.model.pokemon import PokemonMove, PokemonProfile, PokemonStat
from src.model.player import PlayerPokemonMove, PlayerPokemon


class PokemonBattle:
    def __init__(
        self,
        data: PokemonProfile,
        isEnemy: bool,
        playerPokemon: PlayerPokemon = None,
        name: str = None,
        moves: list = None,
        currentHp: int = None,
        level: int = None,
    ):
        self.baseStat = data.stats.copy()
        self.isEnemy = isEnemy

        self.source = playerPokemon
        if playerPokemon:
            self.name = playerPokemon.name.capitalize()
            self.moves = playerPokemon.moves
            self.currentHp = playerPokemon.hp
            self.level = playerPokemon.level
            self.exp = playerPokemon.exp
        else:
            self.name = name.capitalize()
            self.moves = moves
            self.level = level

        self.calculateStats()

        self.maxHp = self.getStat("hp")
        self.currentHp = self.maxHp if not playerPokemon else playerPokemon.hp

        self.types = data.types
        self.evolution = data.evolution
        self.baseExp = data.baseExp

        self.modifiers = {
            "attack": 0,
            "defence": 0,
            "special attack": 0,
            "special defence": 0,
            "speed": 0,
            "accuracy": 0,
            "evasion": 0,
            "crits": 0,
        }

        self.statusEffect = ""
        self.sleepCounter = 0

    def calculateStats(self):
        self.stats = PokemonStat(
            ((2 * self.baseStat.hp * self.level) // 100) + 5 + self.level,
            ((2 * self.baseStat.attack * self.level) // 100) + 5,
            ((2 * self.baseStat.defence * self.level) // 100) + 5,
            ((2 * self.baseStat.special_attack * self.level) // 100) + 5,
            ((2 * self.baseStat.special_defence * self.level) // 100) + 5,
            ((2 * self.baseStat.speed * self.level) // 100) + 5,
        )

    def takeDamage(self, damage: int):
        self.currentHp -= damage
        if self.currentHp <= 0:
            self.currentHp = 0

    def useMove(
        self, move_data: PokemonMove, index: int, pokemon: "PokemonBattle"
    ) -> list[str]:
        text = []

        if self.statusEffect == "paralyzed" and random.random() < 0.25:
            return ["The Pokémon is fully paralyzed!"]

        if self.sleepCounter != 0 and self.statusEffect == "sleep":
            self.sleepCounter -= 1
            return [f"{self.name} was fast asleep."]
        elif self.sleepCounter == 0 and self.statusEffect == "sleep":
            self.statusEffect = ""
            text.append(f"{self.name} woke up!")

        if self.moves[index].pp <= 0:
            return ["But there is no PP left!"]

        self.moves[index].pp -= 1

        if not self.moveAccuracy(move_data.accuracy):
            return ["It missed."]

        self.damageFoePokemon(move_data, pokemon, text)
        self.executeEffects(move_data, pokemon, text)

        return text

    def moveAccuracy(self, accuracy) -> bool:
        if not accuracy:
            return True

        stage = self.modifiers["accuracy"] - self.modifiers["evasion"]
        stage = max(-6, min(6, stage))

        multiplier = 1
        if stage < 0:
            multiplier = 3 / (3 - abs(stage))
        elif stage > 0:
            multiplier = (3 + stage) / 3

        finalAccuracy = accuracy * multiplier
        return random.randint(1, 100) <= finalAccuracy

    def damageFoePokemon(self, move: PokemonMove, pokemon: "PokemonBattle", text: list):
        if not move.power:
            return
        if move.category == "status":
            return

        isPhysical = move.category == "physical"

        d = (
            pokemon.getStat("defence")
            if isPhysical
            else pokemon.getStat("special defence")
        )
        a = self.getStat("attack") if isPhysical else self.getStat("special attack")

        stab = 1.5 if move.type in self.types else 1

        mult = calculateMultiplier(move.type, pokemon.types)

        if mult >= 2:
            text.append("Its super effective.")
        elif mult < 1:
            text.append("Its not very effective.")
        elif mult == 0:
            text.append("No effect.")

        crit = 1
        if self.isCritical():
            d = pokemon.stats.defence if isPhysical else pokemon.stats.special_defence
            crit = 2
            text.append("A critical hit!")

        damage = (
            (((2 * self.level / 5 + 1) * move.power * a / d) / 50 + 2)
            * stab
            * mult
            * crit
        )

        pokemon.takeDamage(round(damage))

    def isCritical(self) -> bool:
        tier = min(self.modifiers["crits"], 4)
        probabilities = {0: 16, 1: 8, 2: 4, 3: 3, 4: 2}
        return random.randint(1, probabilities[tier]) == 1

    def executeEffects(
        self, move: PokemonMove, pokemon: "PokemonBattle", text: list[str]
    ):
        for effect in move.effects:
            destination = self if effect.target == "self" else pokemon

            if effect.type == "stat":
                stat = effect.stat
                change = effect.change
                current_stage = destination.modifiers[stat]

                if change > 0 and current_stage == 6:
                    text.append(f"{destination.name}'s {stat} won't go any higher!")
                    continue
                if change < 0 and current_stage == -6:
                    text.append(f"{destination.name}'s {stat} won't go any lower!")
                    continue

                destination.modifiers[stat] = max(-6, min(6, current_stage + change))

                if change > 0:
                    adj = (
                        "sharply "
                        if change == 2
                        else ("drastically " if change >= 3 else "")
                    )
                    text.append(f"{destination.name}'s {stat} {adj}rose!")
                elif change < 0:
                    adj = (
                        "harshly "
                        if change == -2
                        else ("severely " if change <= -3 else "")
                    )
                    text.append(f"{destination.name}'s {stat} {adj}fell!")
            else:
                chance = effect.chance if effect.chance else 100
                if chance >= random.randint(1, 100):
                    destination.statusEffect = effect.condition
                    if effect.condition == "sleep":
                        destination.sleepCounter = random.randint(2, 5)

    def syncFromSource(self):
        if self.source is None:
            return
        self.currentHp = self.source.hp
        self.level = self.source.level
        self.exp = self.source.exp

    def afterATurn(self) -> list[str]:
        text = []
        if self.statusEffect == "poison":
            damage = self.maxHp // 12.5
            self.takeDamage(damage)
            text.append(f"{self.name} is hurt by poison!")
        return text

    def getHpRatio(self) -> float:
        return self.currentHp / self.maxHp

    def gainExp(self, exp: int):
        old_level = self.level
        self.exp += exp
        old_stats = self.stats.copy()

        while self.exp >= self.expNeeded():
            self.exp -= self.expNeeded()
            self.currentHp = self.maxHp
            self.levelUp()

        hasEvolved = self.evolution and self.evolution.levelCap == self.level

        return {
            "isLeveledUp": self.level > old_level,
            "statsHistory": [old_stats, self.stats.copy()],
            "evolve": {
                "hasEvolved": hasEvolved,
                "to": "" if not self.evolution else self.evolution.to,
            },
        }

    def levelUp(self):
        self.level += 1
        self.calculateStats()

    def getExp(self):
        return (self.baseExp * self.level) // 7

    def getExpRatio(self):
        return self.exp / self.expNeeded()

    def expNeeded(self):
        return self.level**3

    def getStat(self, stat: str) -> int:
        if stat == "hp":
            return self.stats.hp

        fraction = 1
        if self.modifiers[stat] > 0:
            fraction = (2 + self.modifiers[stat]) / 2
        elif self.modifiers[stat] < 0:
            fraction = 2 / (2 + abs(self.modifiers[stat]))

        if stat == "speed" and self.statusEffect == "paralyzed":
            return round(self.stats.speed * fraction * 0.5)
        elif stat == "speed":
            return round(self.stats.speed * fraction)
        elif stat == "attack":
            return round(self.stats.attack * fraction)
        elif stat == "defence":
            return round(self.stats.defence * fraction)
        elif stat == "special attack":
            return round(self.stats.special_attack * fraction)
        elif stat == "special defence":
            return round(self.stats.special_defence * fraction)
