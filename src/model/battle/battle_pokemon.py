import random
from typing import Optional, cast
from src.model.static.pokemon import PokemonMove, PokemonSpecies, PokemonStat
from src.model.save.player import PlayerPokemon
from src.enums.stat import Stat
from src.enums.status_effect import StatusEffect
from src.enums.effect_type import EffectType
from src.model.battle.progression import Progression
from src.model.battle.exp_gain_result import ExpGainResult


class BattlePokemon:
    def __init__(
        self,
        data: PokemonSpecies,
        is_enemy: bool,
        name: str,
        moves: list,
        level: int,
        exp: int,
        current_hp: Optional[int],
        source: Optional[PlayerPokemon],
    ):
        self.is_enemy = is_enemy
        self._apply(data, name, moves, level, exp, current_hp, source)

        # Dispatch over effect.type — add an effect kind by adding a handler,
        # not by editing the loop (mirrors npc_behaviors.make_behavior / bag_system).
        self._effect_handlers = {
            EffectType.STAT: self._apply_stat_effect,
            EffectType.STATUS_CONDITION: self._apply_status_effect,
        }

    @classmethod
    def from_player(
        cls,
        species: PokemonSpecies,
        player_pokemon: PlayerPokemon,
        is_enemy: bool = False,
    ) -> "BattlePokemon":
        return cls(
            species,
            is_enemy,
            player_pokemon.name,
            player_pokemon.moves,
            player_pokemon.level,
            player_pokemon.exp,
            player_pokemon.hp,
            player_pokemon,
        )

    @classmethod
    def from_wild(
        cls,
        species: PokemonSpecies,
        name: str,
        level: int,
        moves: list,
        is_enemy: bool = True,
    ) -> "BattlePokemon":
        return cls(species, is_enemy, name, moves, level, 0, None, None)

    def _apply(
        self,
        data: PokemonSpecies,
        name: str,
        moves: list,
        level: int,
        exp: int,
        current_hp: Optional[int],
        source: Optional[PlayerPokemon],
    ):
        """Build/rebuild this pokemon's state from resolved values. Shared by
        the constructor and switching_pokemon so both stay in sync."""
        self.source = source
        self.name = name.capitalize()
        self.moves = moves
        self._load_species(data)
        self.progression = Progression(level, exp, self.base_exp, self.evolution)
        self.calculate_stats()

        self.max_hp = self.stats.hp
        self.current_hp = current_hp if current_hp is not None else self.max_hp

        self._reset_battle_state()

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

    def _load_species(self, data: PokemonSpecies):
        self.base_stat = cast(PokemonStat, data.stats).copy()
        self.types = data.types
        self.evolution = data.evolution
        self.base_exp = data.baseExp

    def _reset_battle_state(self):
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
        self.status_effect = StatusEffect.NONE
        self.sleep_counter = 0

    def calculate_stats(self):
        self.stats = self.base_stat.at_level(self.level)

    def get_stat(self, stat: Stat) -> int:
        """Return the stage-modified value of a stat (for HP, read self.stats.hp directly)."""
        base = getattr(self.stats, stat, 0)
        stage = self.modifiers.get(stat, 0)
        if stage > 0:
            fraction = (2 + stage) / 2
        elif stage < 0:
            fraction = 2 / (2 + abs(stage))
        else:
            fraction = 1.0

        if stat == Stat.SPEED and self.status_effect == StatusEffect.PARALYSIS:
            fraction *= 0.5

        return round(base * fraction)

    # ------------------------------------------------------------------
    # HP mutation — the only mutator that touches another pokemon
    # is take_damage(), called by BattleSystem after the calculator runs
    # ------------------------------------------------------------------

    def take_damage(self, damage: int):
        self.current_hp = max(0, self.current_hp - damage)

    def switching_pokemon(self, player_pokemon: PlayerPokemon, data: PokemonSpecies):
        self._apply(
            data,
            player_pokemon.name,
            player_pokemon.moves,
            player_pokemon.level,
            player_pokemon.exp,
            player_pokemon.hp,
            player_pokemon,
        )

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
        if self.status_effect == StatusEffect.PARALYSIS and random.random() < 0.25:
            return (["The Pokémon is fully paralyzed!"], False)

        if self.sleep_counter != 0 and self.status_effect == StatusEffect.SLEEP:
            self.sleep_counter -= 1
            return ([f"{self.name} was fast asleep."], False)

        if self.sleep_counter == 0 and self.status_effect == StatusEffect.SLEEP:
            self.status_effect = StatusEffect.NONE
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
            handler = self._effect_handlers.get(effect.type)
            if handler:
                messages.extend(handler(effect, destination))

        return messages

    def _apply_stat_effect(
        self, effect, destination: "BattlePokemon"
    ) -> list[str]:
        messages = []
        stat = effect.stat
        change = effect.change
        current_stage = destination.modifiers[stat]

        if change > 0 and current_stage == 6:
            messages.append(f"{destination.name}'s {stat} won't go any higher!")
            return messages
        if change < 0 and current_stage == -6:
            messages.append(f"{destination.name}'s {stat} won't go any lower!")
            return messages

        destination.modifiers[stat] = max(-6, min(6, current_stage + change))

        if change > 0:
            adj = (
                "sharply " if change == 2 else ("drastically " if change >= 3 else "")
            )
            messages.append(f"{destination.name}'s {stat} {adj}rose!")
        elif change < 0:
            adj = (
                "harshly " if change == -2 else ("severely " if change <= -3 else "")
            )
            messages.append(f"{destination.name}'s {stat} {adj}fell!")

        return messages

    def _apply_status_effect(
        self, effect, destination: "BattlePokemon"
    ) -> list[str]:
        chance = effect.chance if effect.chance else 100
        if chance >= random.randint(1, 100):
            destination.status_effect = effect.condition
            if destination.status_effect == StatusEffect.SLEEP:
                destination.sleep_counter = random.randint(2, 5)
        return []

    # ------------------------------------------------------------------
    # Post-turn tick — self-contained state mutation
    # ------------------------------------------------------------------

    def after_a_turn(self) -> list[str]:
        messages = []
        if self.status_effect == StatusEffect.POISON:
            damage = max(1, int(self.max_hp / 12.5))
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
        self.current_hp = self.source.hp
        self.level = self.source.level
        self.exp = self.source.exp

    def get_hp_ratio(self) -> float:
        return self.current_hp / self.max_hp

    def gain_exp(self, exp: int) -> ExpGainResult:
        old_stats = self.stats.copy()
        levels_gained = self.progression.add_exp(exp)

        if levels_gained:
            self.calculate_stats()
            self.max_hp = self.stats.hp
            self.current_hp = self.max_hp

        return ExpGainResult(
            leveled_up=levels_gained > 0,
            stats_before=old_stats,
            stats_after=self.stats.copy(),
            evolved=self.progression.can_evolve(),
            evolves_to=self.progression.evolves_to,
        )

    def exp_yield(self):
        return self.progression.exp_yield()

    def get_exp_ratio(self):
        return self.progression.exp_ratio()
