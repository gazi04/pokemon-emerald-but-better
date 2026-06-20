import random
from typing import Optional, cast
from src.model.pokemon import PokemonMove, PokemonProfile, PokemonStat
from src.model.player import PlayerPokemon


class PokemonBattle:
    def __init__(
        self,
        data: PokemonProfile,
        isEnemy: bool,
        playerPokemon: Optional[PlayerPokemon] = None,
        name: Optional[str] = None,
        moves: Optional[list] = None,
        currentHp: Optional[int] = None,
        level: Optional[int] = None,
    ):
        self.baseStat = cast(PokemonStat, data.stats).copy()
        self.isEnemy = isEnemy

        self.source = playerPokemon
        if playerPokemon:
            self._loadFromPlayer(playerPokemon)
        else:
            self.name = name.capitalize() if name else "Unknown"
            self.moves = moves if moves else []
            self.level = level if level else 1
            self.exp = 0

        self.calculateStats()

        self.maxHp = self.getStat("hp")
        self.currentHp = self.maxHp if not playerPokemon else playerPokemon.hp

        self.types = data.types
        self.evolution = data.evolution
        self.baseExp = data.baseExp

        self._resetBattleState()

    # ------------------------------------------------------------------
    # Stat management
    # ------------------------------------------------------------------

    def _loadFromPlayer(self, playerPokemon: PlayerPokemon):
        self.name = playerPokemon.name.capitalize()
        self.moves = playerPokemon.moves
        self.level = playerPokemon.level
        self.exp = playerPokemon.exp

    def _loadFromProfile(self, data: PokemonProfile):
        self.baseStat = cast(PokemonStat, data.stats).copy()
        self.types = data.types
        self.evolution = data.evolution
        self.baseExp = data.baseExp

    def _resetBattleState(self):
        self.modifiers = {
            "attack": 0,
            "defence": 0,
            "special_attack": 0,
            "special_defence": 0,
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

    def getStat(self, stat: str) -> int:
        if stat == "hp":
            return self.stats.hp

        stage = self.modifiers.get(stat, 0)
        if stage > 0:
            fraction = (2 + stage) / 2
        elif stage < 0:
            fraction = 2 / (2 + abs(stage))
        else:
            fraction = 1.0

        if stat == "speed" and self.statusEffect == "paralyzed":
            return round(self.stats.speed * fraction * 0.5)
        elif stat == "speed":
            return round(self.stats.speed * fraction)
        elif stat == "attack":
            return round(self.stats.attack * fraction)
        elif stat == "defence":
            return round(self.stats.defence * fraction)
        elif stat == "special_attack":
            return round(self.stats.special_attack * fraction)
        elif stat == "special_defence":
            return round(self.stats.special_defence * fraction)

        return 0

    # ------------------------------------------------------------------
    # HP mutation — the only mutator that touches another pokemon
    # is takeDamage(), called by BattleSystem after the calculator runs
    # ------------------------------------------------------------------

    def takeDamage(self, damage: int):
        self.currentHp = max(0, self.currentHp - damage)

    def switching_pokemon(self, playerPokemon: PlayerPokemon, data: PokemonProfile):
        self.source = playerPokemon

        self._loadFromPlayer(playerPokemon)
        self._loadFromProfile(data)
        self.calculateStats()

        self.maxHp = self.getStat("hp")
        self.currentHp = playerPokemon.hp

        self._resetBattleState()

    # ------------------------------------------------------------------
    # Move gating — status and PP checks
    # Returns (messages, can_move) so BattleSystem decides what to do
    # ------------------------------------------------------------------

    def check_can_move(self, move_index: int) -> tuple[list[str], bool]:
        """
        Check status effects and PP before a move executes.
        Returns (messages, can_move).
        BattleSystem calls this; it never mutates the defender.
        """
        if self.statusEffect == "paralyzed" and random.random() < 0.25:
            return (["The Pokémon is fully paralyzed!"], False)

        if self.sleepCounter != 0 and self.statusEffect == "sleep":
            self.sleepCounter -= 1
            return ([f"{self.name} was fast asleep."], False)

        if self.sleepCounter == 0 and self.statusEffect == "sleep":
            self.statusEffect = ""
            # Woke up — still can't move this turn
            return ([f"{self.name} woke up!"], False)

        if self.moves[move_index].pp <= 0:
            return (["But there is no PP left!"], False)

        # Decrement PP here — move is confirmed to execute
        self.moves[move_index].pp -= 1
        return ([], True)

    # ------------------------------------------------------------------
    # Effect application — stat stage changes and status conditions
    # This is state mutation that belongs in the model; it returns
    # messages instead of accepting a mutable list parameter.
    # ------------------------------------------------------------------

    def executeEffects(self, move: PokemonMove, target: "PokemonBattle") -> list[str]:
        """
        Apply stat/status effects from a move.
        Returns UI messages. Mutates self and target's modifiers/status.
        Called by BattleSystem after damage is applied.
        """
        messages = []

        for effect in move.effects:
            destination = self if effect.target == "self" else target

            if effect.type == "stat":
                stat = cast(str, effect.stat)
                change = cast(int, effect.change)
                current_stage = destination.modifiers[stat]

                if change > 0 and current_stage == 6:
                    messages.append(f"{destination.name}'s {stat} won't go any higher!")
                    continue
                if change < 0 and current_stage == -6:
                    messages.append(f"{destination.name}'s {stat} won't go any lower!")
                    continue

                destination.modifiers[stat] = max(-6, min(6, current_stage + change))

                if change > 0:
                    adj = (
                        "sharply "
                        if change == 2
                        else ("drastically " if change >= 3 else "")
                    )
                    messages.append(f"{destination.name}'s {stat} {adj}rose!")
                elif change < 0:
                    adj = (
                        "harshly "
                        if change == -2
                        else ("severely " if change <= -3 else "")
                    )
                    messages.append(f"{destination.name}'s {stat} {adj}fell!")
            else:
                chance = cast(int, effect.chance if effect.chance else 100)
                if chance >= random.randint(1, 100):
                    destination.statusEffect = effect.condition
                    if effect.condition == "sleep":
                        destination.sleepCounter = random.randint(2, 5)

        return messages

    # ------------------------------------------------------------------
    # Post-turn tick — self-contained state mutation
    # ------------------------------------------------------------------

    def afterATurn(self) -> list[str]:
        messages = []
        if self.statusEffect == "poison":
            damage = max(1, int(self.maxHp / 12.5))
            self.takeDamage(damage)
            messages.append(f"{self.name} is hurt by poison!")
        return messages

    # ------------------------------------------------------------------
    # Exp and levelling
    # ------------------------------------------------------------------

    def syncFromSource(self):
        if self.source is None:
            return
        self.currentHp = self.source.hp
        self.level = self.source.level
        self.exp = self.source.exp

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

        hasEvolved = self.evolution and self.evolution.levelCap <= self.level

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
