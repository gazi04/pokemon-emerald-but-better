import random
from typing import Optional, cast
from src.model.static.pokemon import PokemonMove, PokemonSpecies, PokemonStat
from src.model.save.player import PlayerPokemon
from src.model.battle.stat import Stat
from src.model.battle.status_effect import StatusEffect
from src.model.battle.effect_type import EffectType
from src.model.battle.progression import Progression


class BattlePokemon:
    def __init__(
        self,
        data: PokemonSpecies,
        isEnemy: bool,
        playerPokemon: Optional[PlayerPokemon] = None,
        name: Optional[str] = None,
        moves: Optional[list] = None,
        currentHp: Optional[int] = None,
        level: Optional[int] = None,
    ):
        self.isEnemy = isEnemy
        self._loadFromProfile(data)

        self.source = playerPokemon
        if playerPokemon:
            self.name = playerPokemon.name.capitalize()
            self.moves = playerPokemon.moves
            start_level = playerPokemon.level
            start_exp = playerPokemon.exp
        else:
            self.name = name.capitalize() if name else "Unknown"
            self.moves = moves if moves else []
            start_level = level if level else 1
            start_exp = 0

        self.progression = Progression(
            start_level, start_exp, self.baseExp, self.evolution
        )
        self.calculate_stats()

        self.maxHp = self.get_stat(Stat.HP)
        self.currentHp = self.maxHp if not playerPokemon else playerPokemon.hp

        self._resetBattleState()

    # ------------------------------------------------------------------
    # Progression is delegated to self.progression; level and exp stay
    # readable/writable on the battle object for combat code that needs them.
    # ------------------------------------------------------------------

    @property
    def level(self) -> int:
        return self.progression.level

    @level.setter
    def level(self, value: int):
        self.progression.level = value

    @property
    def exp(self) -> int:
        return self.progression.exp

    @exp.setter
    def exp(self, value: int):
        self.progression.exp = value

    # ------------------------------------------------------------------
    # Stat management
    # ------------------------------------------------------------------

    def _loadFromProfile(self, data: PokemonSpecies):
        self.baseStat = cast(PokemonStat, data.stats).copy()
        self.types = data.types
        self.evolution = data.evolution
        self.baseExp = data.baseExp

    def _resetBattleState(self):
        self.modifiers: dict[Stat, int] = {
            Stat.ATTACK: 0,
            Stat.DEFENCE: 0,
            Stat.SPECIAL_ATTACK: 0,
            Stat.SPECIAL_DEFENCE: 0,
            Stat.SPEED: 0,
            Stat.ACCURACY: 0,
            Stat.EVASION: 0,
            Stat.CRITS: 0,
        }
        self.statusEffect = StatusEffect.NONE
        self.sleepCounter = 0

    def calculate_stats(self):
        self.stats = self.baseStat.at_level(self.level)

    def get_stat(self, stat: Stat) -> int:
        base = getattr(self.stats, stat, 0)
        if stat == Stat.HP:
            return base

        stage = self.modifiers.get(stat, 0)
        if stage > 0:
            fraction = (2 + stage) / 2
        elif stage < 0:
            fraction = 2 / (2 + abs(stage))
        else:
            fraction = 1.0

        if stat == Stat.SPEED and self.statusEffect == StatusEffect.PARALYSIS:
            fraction *= 0.5

        return round(base * fraction)

    # ------------------------------------------------------------------
    # HP mutation — the only mutator that touches another pokemon
    # is take_damage(), called by BattleSystem after the calculator runs
    # ------------------------------------------------------------------

    def take_damage(self, damage: int):
        self.currentHp = max(0, self.currentHp - damage)

    def switching_pokemon(self, playerPokemon: PlayerPokemon, data: PokemonSpecies):
        self.source = playerPokemon

        self.name = playerPokemon.name.capitalize()
        self.moves = playerPokemon.moves
        self._loadFromProfile(data)
        self.progression = Progression(
            playerPokemon.level, playerPokemon.exp, self.baseExp, self.evolution
        )
        self.calculate_stats()

        self.maxHp = self.get_stat(Stat.HP)
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
        if self.statusEffect == StatusEffect.PARALYSIS and random.random() < 0.25:
            return (["The Pokémon is fully paralyzed!"], False)

        if self.sleepCounter != 0 and self.statusEffect == StatusEffect.SLEEP:
            self.sleepCounter -= 1
            return ([f"{self.name} was fast asleep."], False)

        if self.sleepCounter == 0 and self.statusEffect == StatusEffect.SLEEP:
            self.statusEffect = StatusEffect.NONE
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

    def execute_effects(self, move: PokemonMove, target: "BattlePokemon") -> list[str]:
        """
        Apply stat/status effects from a move.
        Returns UI messages. Mutates self and target's modifiers/status.
        Called by BattleSystem after damage is applied.
        """
        messages = []

        for effect in move.effects:
            destination = self if effect.target == "self" else target

            if effect.type == EffectType.STAT:
                stat = Stat(cast(str, effect.stat))
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
                    destination.statusEffect = StatusEffect(cast(str, effect.condition))
                    if destination.statusEffect == StatusEffect.SLEEP:
                        destination.sleepCounter = random.randint(2, 5)

        return messages

    # ------------------------------------------------------------------
    # Post-turn tick — self-contained state mutation
    # ------------------------------------------------------------------

    def after_a_turn(self) -> list[str]:
        messages = []
        if self.statusEffect == StatusEffect.POISON:
            damage = max(1, int(self.maxHp / 12.5))
            self.take_damage(damage)
            messages.append(f"{self.name} is hurt by poison!")
        return messages

    # ------------------------------------------------------------------
    # Exp and levelling — delegated to self.progression; this object only
    # reacts to a level-up by recomputing combat stats and healing.
    # ------------------------------------------------------------------

    def sync_from_source(self):
        if self.source is None:
            return
        self.currentHp = self.source.hp
        self.level = self.source.level
        self.exp = self.source.exp

    def get_hp_ratio(self) -> float:
        return self.currentHp / self.maxHp

    def gain_exp(self, exp: int):
        old_stats = self.stats.copy()
        levels_gained = self.progression.add_exp(exp)

        if levels_gained:
            self.calculate_stats()
            self.maxHp = self.get_stat(Stat.HP)
            self.currentHp = self.maxHp

        return {
            "isLeveledUp": levels_gained > 0,
            "statsHistory": [old_stats, self.stats.copy()],
            "evolve": {
                "hasEvolved": self.progression.can_evolve(),
                "to": self.progression.evolves_to,
            },
        }

    def exp_yield(self):
        return self.progression.exp_yield()

    def get_exp_ratio(self):
        return self.progression.exp_ratio()
