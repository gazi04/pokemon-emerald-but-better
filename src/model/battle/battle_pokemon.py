import random
from typing import Optional, cast
from src.model.static.pokemon import PokemonMove, PokemonSpecies, PokemonStat
from src.model.save.player import PlayerPokemon
from src.enums.stat import Stat
from src.enums.status_effect import StatusEffect
from src.enums.effect_type import EffectType
from src.model.battle.progression import Progression
from src.model.battle.exp_gain_result import ExpGainResult
from src.model.static.ability import Ability, AbilityEffect


class BattlePokemon:
    def __init__(
        self,
        data: PokemonSpecies,
        is_enemy: bool,
        name: str,
        moves: list,
        level: int,
        exp: int,
        ability: Ability,
        current_hp: Optional[int],
        source: Optional[PlayerPokemon],
    ):
        self.is_enemy = is_enemy
        self._apply(data, name, moves, level, exp, ability, current_hp, source)

        # Dispatch over effect.type — add an effect kind by adding a handler,
        # not by editing the loop (mirrors npc_behaviors.make_behavior / bag_system).
        self._effect_handlers = {
            EffectType.STAT: self._apply_stat_effect,
            EffectType.STATUS_CONDITION: self._apply_status_effect,
        }

    @classmethod
    def from_player(
        cls,
        ability: Ability,
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
            ability,
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
        ability: Ability,
        is_enemy: bool = True,
    ) -> "BattlePokemon":
        return cls(species, is_enemy, name, moves, level, 0, ability, None, None)

    def _apply(
        self,
        data: PokemonSpecies,
        name: str,
        moves: list,
        level: int,
        exp: int,
        ability: Ability,
        current_hp: Optional[int],
        source: Optional[PlayerPokemon],
    ):
        """Build/rebuild this pokemon's state from resolved values. Shared by
        the constructor and switching_pokemon so both stay in sync."""
        self.source = source
        self.name = name.capitalize()
        self.moves = moves
        self.ability = ability
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
        self.flinched = False
        self.confusion_counter = 0

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
            
        if stat == Stat.ATTACK and self.status_effect == StatusEffect.BURN:
            fraction *= 0.5

        return round(base * fraction)

    # ------------------------------------------------------------------
    # HP mutation — the only mutator that touches another pokemon
    # is take_damage(), called by BattleSystem after the calculator runs
    # ------------------------------------------------------------------

    def take_damage(self, damage: int):
        self.current_hp = max(0, self.current_hp - damage)

    def switching_pokemon(self, player_pokemon: PlayerPokemon, ability: Ability, data: PokemonSpecies):
        self._apply(
            data,
            player_pokemon.name,
            player_pokemon.moves,
            player_pokemon.level,
            player_pokemon.exp,
            ability,
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
        if self.flinched:
            self.flinched = False
            return (["The Pokemon is flinched!"], False)
        
        if self.status_effect == StatusEffect.PARALYSIS and random.random() < 0.25:
            return (["The Pokemon is fully paralyzed!"], False)
        
        if self.status_effect == StatusEffect.FREEZE:
            return (["The Pokemon is freezed!"], False)

        if self.sleep_counter != 0 and self.status_effect == StatusEffect.SLEEP:
            self.sleep_counter -= 1
            return ([f"{self.name} was fast asleep."], False)

        if self.sleep_counter == 0 and self.status_effect == StatusEffect.SLEEP:
            self.status_effect = StatusEffect.NONE
            # Woke up — still can't move this turn
            return ([f"{self.name} woke up!"], False)

        # Confusion — volatile; its message carries through even if the move
        # still goes off, so accumulate rather than early-return on a clear.
        pre_messages: list[str] = []
        if self.confusion_counter > 0:
            self.confusion_counter -= 1
            if self.confusion_counter == 0:
                pre_messages.append(f"{self.name} snapped out of its confusion!")
            else:
                pre_messages.append(f"{self.name} is confused!")
                if random.random() < 1 / 3:
                    self.take_damage(self._confusion_self_damage())
                    pre_messages.append("It hurt itself in its confusion!")
                    return (pre_messages, False)

        if self.moves[move_index].pp <= 0:
            return (pre_messages + ["But there is no PP left!"], False)

        # Decrement PP here — move is confirmed to execute
        self.moves[move_index].pp -= 1
        return (pre_messages, True)

    def _confusion_self_damage(self) -> int:
        """A typeless 40-power physical hit against the pokemon's own defence."""
        attack = self.get_stat(Stat.ATTACK)
        defence = max(1, self.get_stat(Stat.DEFENCE))
        raw = ((2 * self.level / 5 + 2) * 40 * attack / defence) / 50 + 2
        return max(1, round(raw))

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
        message = []
        chance = effect.chance if effect.chance else 100
        if chance >= random.randint(1, 100):
            if effect.condition == StatusEffect.CONFUSION:
                # Volatile — independent of the major status condition.
                if destination.confusion_counter == 0:
                    destination.confusion_counter = random.randint(2, 5)
                    message.append(f"{destination.name} became confused!")
                else:
                    message.append(f"{destination.name} is already confused.")
                return message
            if destination.status_effect == StatusEffect.NONE and effect.condition != StatusEffect.FLINCH:
                message.append(f"{destination.name} was {effect.condition}.")
                
                destination.status_effect = effect.condition
                if destination.status_effect == StatusEffect.SLEEP:
                    destination.sleep_counter = random.randint(2, 5)
            elif destination.status_effect != StatusEffect.NONE or effect.condition != StatusEffect.FLINCH:
                message.append(f"{destination.name} already has a condition.")
                
            if effect.condition == StatusEffect.FLINCH:
                destination.flinched = True
            
        return message

    # ------------------------------------------------------------------
    # Post-turn tick — self-contained state mutation
    # ------------------------------------------------------------------

    def after_a_turn(self) -> list[str]:
        messages = []
        
        if self.status_effect == StatusEffect.POISON:
            damage = max(1, int(self.max_hp / 12.5))
            self.take_damage(damage)
            messages.append(f"{self.name} is hurt by poison!")
        
        if self.status_effect == StatusEffect.BURN:
            damage = max(1, int(self.max_hp / 8))
            self.take_damage(damage)
            messages.append(f"{self.name} is burned!")
        
        if self.status_effect == StatusEffect.FREEZE and random.random() < 0.2:
            self.status_effect = StatusEffect.NONE
            messages.append(f"{self.name} is thaw!")
        
        return messages
    
    # ------------------------------------------------------------------
    # Abilities — data-driven hooks fired by BattleSystem during a move.
    # Mirrors the move-effect dispatch above: each trigger reads this
    # pokemon's ability effects and applies the ones whose condition holds.
    # ------------------------------------------------------------------

    def _ability_effects(self, trigger: str) -> list[AbilityEffect]:
        if not self.ability or not self.ability.effects:
            return []
        return [e for e in self.ability.effects if e.trigger == trigger]

    def _ability_condition_met(self, effect:AbilityEffect, move:PokemonMove = None) -> bool:
        """Gate an ability effect on its `condition` (None == always)."""
        condition = effect.condition
        if not condition:
            return True
        if condition == "low_hp":
            return self.current_hp <= self.max_hp / 3
        if condition == "contact" and move:
            return move is not None and move.category == "physical"
        if condition == "ground_type" and move:
            return move is not None and move.type == "ground"
        return False

    def ability_attack_multiplier(self, move:PokemonMove) -> tuple[float, list[str]]:
        """Attacker hook (trigger 'on_attack'). Returns a damage multiplier and
        any UI messages — e.g. Blaze powering up the attack at low HP."""
        multiplier = 1.0
        messages: list[str] = []
        for effect in self._ability_effects("on_attack"):
            if effect.type != "damage_boost":
                continue
            if not self._ability_condition_met(effect, move):
                continue
            if move.type != effect.move_type:
                continue
            multiplier *= 1 + (effect.change or 0) / 100
            messages.append(f"{self.name}'s {self.ability.name} powered up the move!")
        
        return multiplier, messages

    def immunity_to(self, move:PokemonMove) -> Optional[str]:
        """Defender hook. Returns a message if this pokemon's ability makes it
        immune to `move` (e.g. Levitate vs Ground), else None."""
        for effect in self._ability_effects("on_hit"):
            if effect.type in ["immunity", "absorb"] and self._ability_condition_met(effect, move):
                return f"It doesn't affect {self.name}…"
        return None

    def on_hit(self, attacker: "BattlePokemon", move: PokemonMove) -> list[str]:
        messages: list[str] = []
        for effect in self._ability_effects("on_hit"):
            if not self._ability_condition_met(effect, move):
                continue
            chance = effect.chance if effect.chance is not None else 1.0
            if random.random() >= chance:
                continue

            if effect.type == "status":
                victim = attacker if effect.target == "enemy" else self
                applied, message = self._apply_status_effect_ability(effect, victim)
                if applied:
                    messages.append(message)

            elif effect.type == "absorb":
                messages.extend(self._heal_from_ability(effect))

        return messages
    
    def _apply_status_effect_ability(self, effect:AbilityEffect, destination:"BattlePokemon"):
        status = self._status_from(effect.status)
        if status is None or destination.status_effect != StatusEffect.NONE:
            return (False, "")

        destination.status_effect = status
        if status == StatusEffect.SLEEP:
            destination.sleep_counter = random.randint(2, 5)
            
        return (True, f"{destination.name} was {status.value} by {self.name}'s {self.ability.name}!")
    
    def _heal_from_ability(self, effect: AbilityEffect) -> list[str]:
        if effect.change is None:
            return []

        regained = int(self.max_hp * effect.change / 100)
        self.current_hp = min(self.max_hp, self.current_hp + regained)
        return [f"{self.name} restored HP using {self.ability.name}!"]
    
    def on_switch_in(self, opponent: "BattlePokemon") -> list[str]:
        messages = []
        for effect in self._ability_effects("on_switch_in"):
            if not self._ability_condition_met(effect):
                continue

            if effect.type == "stat_change":
                target = opponent if effect.target == "enemy" else self
                messages.extend(self._apply_stat_effect(effect, target))
                messages.append(f"{self.name}'s {self.ability.name} took effect!")

            elif effect.type == "status":
                target = opponent if effect.target == "enemy" else self
                applied, message = self._apply_status_effect_ability(effect, target)
                if applied:
                    messages.append(message)

        return messages
    
    def on_turn_end(self, opponent: "BattlePokemon") -> list[str]:
        messages = []
        for effect in self._ability_effects("on_turn_end"):
            if not self._ability_condition_met(effect):
                continue

            if effect.type == "stat_change":
                target = opponent if effect.target == "enemy" else self
                messages.extend(self._apply_stat_effect(effect, target))

            elif effect.type == "cure_status":
                if self.status_effect != StatusEffect.NONE:
                    chance = effect.chance if effect.chance is not None else 1.0
                    if random.random() < chance:
                        cured = self.status_effect.value
                        self.status_effect = StatusEffect.NONE
                        self.sleep_counter = 0
                        messages.append(f"{self.name}'s {self.ability.name} cured its {cured}!")

            elif effect.type == "heal":
                messages.extend(self._heal_from_ability(effect))

        return messages

    @staticmethod
    def _status_from(value) -> Optional[StatusEffect]:
        if not value:
            return None
        try:
            return StatusEffect(value)
        except ValueError:
            return None

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
