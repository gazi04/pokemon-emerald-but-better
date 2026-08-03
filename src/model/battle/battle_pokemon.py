import copy
import random
from typing import cast
from src.model.static.pokemon import PokemonMove, PokemonSpecies, PokemonStat
from src.model.save.player import PlayerPokemon, PlayerPokemonMove
from src.enums.stat import Stat
from src.enums.status_effect import StatusEffect
from src.enums.effect_type import EffectType
from src.model.battle.progression import Progression
from src.model.battle.exp_gain_result import ExpGainResult
from src.model.static.ability import Ability, AbilityEffect
from src.model.static.item import ItemSpecies

MAX_MOVES = 4


class BattlePokemon:
    def __init__(
        self,
        data: PokemonSpecies,
        is_enemy: bool,
        name: str,
        moves: list[PlayerPokemonMove],
        level: int,
        exp: int,
        ability: Ability | None,
        current_hp: int | None,
        source: PlayerPokemon | None,
        held_item: ItemSpecies | None = None,
    ):
        self.is_enemy = is_enemy
        self._apply(
            data, name, moves, level, exp, ability, current_hp, source, held_item
        )

        # Dispatch over effect.type — add an effect kind by adding a handler,
        # not by editing the loop (mirrors npc_behaviors.make_behavior / bag_system).
        self._effect_handlers = {
            EffectType.STAT: self._apply_stat_effect,
            EffectType.STATUS_CONDITION: self._apply_status_effect,
            EffectType.PROTECT: self._apply_protect,
        }

    @classmethod
    def from_player(
        cls,
        ability: Ability | None,
        species: PokemonSpecies,
        player_pokemon: PlayerPokemon,
        is_enemy: bool = False,
        held_item: ItemSpecies | None = None,
    ) -> BattlePokemon:
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
            held_item,
        )

    @classmethod
    def from_wild(
        cls,
        species: PokemonSpecies,
        name: str,
        level: int,
        moves: list,
        ability: Ability | None,
        is_enemy: bool = True,
        held_item: ItemSpecies | None = None,
    ) -> BattlePokemon:
        return cls(
            species, is_enemy, name, moves, level, 0, ability, None, None, held_item
        )

    def _apply(
        self,
        data: PokemonSpecies,
        name: str,
        moves: list[PlayerPokemonMove],
        level: int,
        exp: int,
        ability: Ability | None,
        current_hp: int | None,
        source: PlayerPokemon | None,
        held_item: ItemSpecies | None = None,
    ):
        """Build/rebuild this pokemon's state from resolved values. Shared by
        the constructor and switching_pokemon so both stay in sync."""
        self.source = source
        self.name = name.capitalize()
        self.moves = moves
        self.ability = ability
        self.held_item = held_item
        self._load_species(data)
        self.progression = Progression(
            level, exp, self.base_exp, self.evolution)
        self.calculate_stats()

        self.max_hp = self.stats.hp
        self.current_hp = current_hp if current_hp is not None else self.max_hp

        self._reset_battle_state()

        # Carry a persisted major status into battle (e.g. still poisoned).
        if source is not None and source.status_condition:
            self.status_effect = StatusEffect(source.status_condition)

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
        self.learnset = data.learnset

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
        self.is_first_turn = True
        self.is_protected = False
        self.confusion_counter = 0

    def calculate_stats(self):
        self.stats = self.base_stat.at_level(self.level)

    def copy_for_simulation(self) -> BattlePokemon:
        """Cheap clone for AI lookahead — only current_hp, status_effect, and
        modifiers get mutated during simulation, so a shallow copy plus an
        isolated modifiers dict is enough. Avoids copy.deepcopy() dragging
        along the entire species/save-data graph (source, moves, stats...)."""
        clone = copy.copy(self)
        clone.modifiers = dict(self.modifiers)
        return clone

    def get_stat(self, stat: Stat) -> int:
        """Return the stage-modified value of a stat.

        For HP, read self.stats.hp directly. The formula itself lives on
        PokemonStat so it is shared with the damage calculator.
        """
        return self.stats.effective(stat, self.modifiers, self.status_effect)

    # ------------------------------------------------------------------
    # HP mutation — the only mutator that touches another pokemon
    # is take_damage(), called by BattleSystem after the calculator runs
    # ------------------------------------------------------------------

    def take_damage(self, damage: int):
        self.current_hp = max(0, self.current_hp - damage)

    def switching_pokemon(
        self,
        player_pokemon: PlayerPokemon,
        ability: Ability | None,
        data: PokemonSpecies,
        held_item: ItemSpecies | None = None,
    ):
        self._apply(
            data,
            player_pokemon.name,
            player_pokemon.moves,
            player_pokemon.level,
            player_pokemon.exp,
            ability,
            player_pokemon.hp,
            player_pokemon,
            held_item,
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
                pre_messages.append(
                    f"{self.name} snapped out of its confusion!")
            else:
                pre_messages.append(f"{self.name} is confused!")
                if random.random() < 1 / 3:
                    self.take_damage(self._confusion_self_damage())
                    pre_messages.append("It hurt itself in its confusion!")
                    return (pre_messages, False)

        if self.moves[move_index].pp <= 0:
            return ([*pre_messages, "But there is no PP left!"], False)

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

    def execute_effects(self, move: PokemonMove, target: BattlePokemon) -> list[str]:
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

    def _apply_stat_effect(self, effect, destination: BattlePokemon) -> list[str]:
        messages = []
        stat = effect.stat
        change = effect.change
        current_stage = destination.modifiers[stat]
        
        if self._ability_blocks_stat_drop(stat, change):
            return []

        if change > 0 and current_stage == 6:
            messages.append(
                f"{destination.name}'s {stat} won't go any higher!")
            return messages
        if change < 0 and current_stage == -6:
            messages.append(f"{destination.name}'s {stat} won't go any lower!")
            return messages

        destination.modifiers[stat] = max(-6, min(6, current_stage + change))

        if change > 0:
            adj = "sharply " if change == 2 else (
                "drastically " if change >= 3 else "")
            messages.append(f"{destination.name}'s {stat} {adj}rose!")
        elif change < 0:
            adj = "harshly " if change == - \
                2 else ("severely " if change <= -3 else "")
            messages.append(f"{destination.name}'s {stat} {adj}fell!")

        return messages

    def _apply_status_effect(self, effect, destination: BattlePokemon) -> list[str]:
        message = []
        chance = effect.chance if effect.chance else 100
        if chance >= random.randint(1, 100):
            if self._has_status_immunity(effect.condition):
                return []

            if effect.condition == StatusEffect.CONFUSION:
                if destination.confusion_counter == 0:
                    destination.confusion_counter = random.randint(2, 5)
                    message.append(f"{destination.name} became confused!")
                else:
                    message.append(f"{destination.name} is already confused.")
                return message

            if effect.condition == StatusEffect.FLINCH:
                destination.flinched = True
                return []

            if destination.status_effect == StatusEffect.NONE:
                if (
                    effect.condition == StatusEffect.BURN
                    and "fire" in destination.types
                ):
                    return []
                if effect.condition == StatusEffect.POISON and (
                    "poison" in destination.types or "steel" in destination.types
                ):
                    return []
                if effect.condition == StatusEffect.FREEZE and (
                    "fire" in destination.types or "ice" in destination.types
                ):
                    return []
                if effect.condition == StatusEffect.PARALYSIS and (
                    "ground" in destination.types or "electric" in destination.types
                ):
                    return []

                message.append(f"{destination.name} was {effect.condition}.")

                destination.status_effect = effect.condition
                if destination.status_effect == StatusEffect.SLEEP:
                    destination.sleep_counter = random.randint(2, 5)
            else:
                message.append(f"{destination.name} already has a condition.")

        return message

    def _apply_protect(self, effect, destination: BattlePokemon) -> list[str]:
        destination.is_protected = True
        return [f"{destination.name} protected itself!"]

    # ------------------------------------------------------------------
    # Post-turn tick — self-contained state mutation
    # ------------------------------------------------------------------

    def after_a_turn(self) -> list[str]:
        messages = []

        if self.status_effect == StatusEffect.POISON:
            damage = max(1, int(self.max_hp / 8))
            self.take_damage(damage)
            messages.append(f"{self.name} is hurt by poison!")

        if self.status_effect == StatusEffect.BURN:
            damage = max(1, int(self.max_hp / 8))
            self.take_damage(damage)
            messages.append(f"{self.name} is burned!")

        if self.status_effect == StatusEffect.FREEZE and random.random() < 0.2:
            self.status_effect = StatusEffect.NONE
            messages.append(f"{self.name} is thaw!")

        self.is_protected = False
        self.is_first_turn = False

        return messages

    # ------------------------------------------------------------------
    # Abilities — data-driven hooks fired by BattleSystem during a move.
    # Mirrors the move-effect dispatch above: each trigger reads this
    # pokemon's ability effects and applies the ones whose condition holds.
    # ------------------------------------------------------------------

    @property
    def ability_name(self) -> str:
        """The ability's name, for messages. Every caller is reached through
        `_ability_effects`, which yields nothing when there's no ability, so the
        empty fallback is unreachable in practice."""
        return self.ability.name if self.ability else ""

    def _ability_effects(self, trigger: str) -> list[AbilityEffect]:
        if not self.ability or not self.ability.effects:
            return []
        return [e for e in self.ability.effects if e.trigger == trigger]

    def _ability_condition_met(
        self, effect: AbilityEffect, move: PokemonMove | None = None
    ) -> bool:
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

    def ability_attack_multiplier(self, move: PokemonMove) -> tuple[float, list[str]]:
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
            messages.append(
                f"{self.name}'s {self.ability_name} powered up the move!")

        return multiplier, messages

    def immunity_to(self, move: PokemonMove) -> str | None:
        """Defender hook. Returns a message if this pokemon's ability makes it
        immune to `move` (e.g. Levitate vs Ground), else None."""
        for effect in self._ability_effects("on_hit"):
            if effect.type in ["immunity", "absorb"] and self._ability_condition_met(
                effect, move
            ):
                return f"It doesn't affect {self.name}…"
        return None

    def _has_status_immunity(self, status: StatusEffect) -> bool:
        """Returns True if this pokemon's ability makes it immune to the given status condition.
        e.g. Limber prevents paralysis, Immunity prevents poison, Water Veil prevents burn."""
        return any(
            effect.type == "immunity_status_effect" and effect.status == status
            for effect in self._ability_effects("on_hit")
        )
        
    def _ability_blocks_stat_drop(self, stat: Stat, change: int) -> bool:
        """
        Returns True if this pokemon's ability prevents a stat from being lowered.
        e.g. Clear Body / White Smoke block any move or ability that would reduce a stat stage.
        Only applies when change is negative (a drop); boosts are never blocked.
        """
        return change < 0 and any(
            effect.type == "immunity_stat_drop" and effect.stat == stat
            for effect in self._ability_effects("on_stat_change")
        )

    def on_hit(self, attacker: BattlePokemon, move: PokemonMove) -> list[str]:
        messages: list[str] = []
        for effect in self._ability_effects("on_hit"):
            if not self._ability_condition_met(effect, move):
                continue
            chance = effect.chance if effect.chance is not None else 1.0
            if random.random() >= chance:
                continue

            if effect.type == "status":
                victim = attacker if effect.target == "enemy" else self
                applied, message = self._apply_status_effect_ability(
                    effect, victim)
                if applied:
                    messages.append(message)

            elif effect.type == "absorb":
                messages.extend(self._heal_from_ability(effect))

        return messages

    def _apply_status_effect_ability(
        self, effect: AbilityEffect, destination: BattlePokemon
    ):
        status = self._status_from(effect.status)
        if status is None or destination.status_effect != StatusEffect.NONE:
            return (False, "")

        if self._has_status_immunity(status):
            return (False, "")

        if effect.condition == StatusEffect.BURN and "fire" in destination.types:
            return (False, "")
        if effect.condition == StatusEffect.POISON and (
            "poison" in destination.types or "steel" in destination.types
        ):
            return (False, "")
        if effect.condition == StatusEffect.PARALYSIS and (
            "ground" in destination.types or "electric" in destination.types
        ):
            return (False, "")
        if effect.condition == StatusEffect.FREEZE and (
            "fire" in destination.types or "ice" in destination.types
        ):
            return (False, "")

        destination.status_effect = status
        if status == StatusEffect.SLEEP:
            destination.sleep_counter = random.randint(2, 5)

        return (
            True,
            f"{destination.name} was {status.value} by "
            f"{self.name}'s {self.ability_name}!",
        )

    def _heal_from_ability(self, effect: AbilityEffect) -> list[str]:
        if effect.change is None:
            return []

        regained = int(self.max_hp * effect.change / 100)
        self.current_hp = min(self.max_hp, self.current_hp + regained)
        return [f"{self.name} restored HP using {self.ability_name}!"]

    # ------------------------------------------------------------------
    # Held items — data-driven hooks fired by BattleSystem, mirroring the
    # ability hooks. Berries are consumed (removed from the holder + its save
    # source); passive items (choice/type/orb) stay equipped.
    # ------------------------------------------------------------------

    def _consume_item(self) -> None:
        self.held_item = None
        if self.source is not None:
            self.source.held_item = None

    def item_attack_multiplier(self, move: PokemonMove) -> float:
        """Passive offensive item multiplier folded into damage: Life Orb / type
        boosters (damage_multiplier) and Choice Band/Specs (stat_multiplier)."""
        item = self.held_item
        if not item or not item.battle_attributes:
            return 1.0
        attrs = item.battle_attributes
        multiplier = 1.0

        if attrs.damage_multiplier:
            move_type = (
                item.battle_condition.move_type if item.battle_condition else None
            )
            if move_type is None or move.type == move_type:
                multiplier *= attrs.damage_multiplier

        if attrs.stat_multiplier:
            stat = attrs.stat_multiplier.get("stat")
            mult = attrs.stat_multiplier.get("multiplier", 1.0)
            if (stat == "attack" and move.category == "physical") or (
                stat == "special_attack" and move.category == "special"
            ):
                multiplier *= mult

        return multiplier

    def item_recoil_self(self, move: PokemonMove) -> list[str]:
        """Life Orb: the attacker loses HP after landing a damaging move."""
        item = self.held_item
        if not item or not move.power:
            return []
        for effect in item.effects:
            if effect.type == EffectType.RECOIL_TO_SELF and effect.percent:
                self.take_damage(
                    max(1, int(self.max_hp * effect.percent / 100)))
                return [f"{self.name} was hurt by its {item.name}!"]
        return []

    def item_on_hit(self, attacker: BattlePokemon, move: PokemonMove) -> list[str]:
        """Rocky Helmet: the holder's item hurts the attacker on a contact hit."""
        item = self.held_item
        if item is None:
            return []
        cond = item.battle_condition
        if not cond or cond.trigger != "on_hit":
            return []
        if cond.contact_only and move.category != "physical":
            return []
        for effect in item.effects:
            if effect.type == EffectType.RECOIL_TO_ATTACKER and effect.percent:
                attacker.take_damage(
                    max(1, int(attacker.max_hp * effect.percent / 100))
                )
                return [f"{attacker.name} was hurt by {self.name}'s {item.name}!"]
        return []

    def item_turn_end(self) -> list[str]:
        """Leftovers: restore a little HP at the end of the turn."""
        item = self.held_item
        if item is None:
            return []
        cond = item.battle_condition
        if not cond or cond.trigger != "on_turn_end" or self.current_hp >= self.max_hp:
            return []
        for effect in item.effects:
            if effect.type == EffectType.HEAL and effect.percent:
                healed = max(1, int(self.max_hp * effect.percent / 100))
                self.current_hp = min(self.max_hp, self.current_hp + healed)
                return [f"{self.name} restored a little HP using its {item.name}!"]
        return []

    def consume_berry_on_hp(self) -> list[str]:
        """Pinch berries (Sitrus/Oran heal, Salac/Liechi stat) — eaten when HP
        drops to/below the berry's threshold."""
        item = self.held_item
        if item is None:
            return []
        cond = item.battle_condition
        if not cond or cond.trigger != "hp_threshold" or self.current_hp <= 0:
            return []
        if self.current_hp / self.max_hp > (cond.threshold or 0):
            return []

        messages = [f"{self.name} ate its {item.name}!"]
        for effect in item.effects:
            if effect.type == EffectType.HEAL:
                healed = (
                    max(1, int(self.max_hp * effect.percent / 100))
                    if effect.percent
                    else (effect.amount or 0)
                )
                self.current_hp = min(self.max_hp, self.current_hp + healed)
                messages.append(f"{self.name} restored its HP.")
            elif effect.type == EffectType.STAT and effect.stat:
                messages.extend(
                    self._raise_stat_from_item(
                        Stat(effect.stat), effect.change or 1)
                )
        self._consume_item()
        return messages

    def consume_berry_on_status(self) -> list[str]:
        """Lum Berry: cure any status the moment one is inflicted."""
        item = self.held_item
        if item is None:
            return []
        cond = item.battle_condition
        if not cond or cond.trigger != "on_status":
            return []
        if self.status_effect == StatusEffect.NONE and self.confusion_counter == 0:
            return []
        name = item.name
        self.status_effect = StatusEffect.NONE
        self.sleep_counter = 0
        self.confusion_counter = 0
        self._consume_item()
        return [f"{self.name}'s {name} cured its status!"]

    def _raise_stat_from_item(self, stat: Stat, change: int) -> list[str]:
        current = self.modifiers.get(stat, 0)
        if current >= 6:
            return [f"{self.name}'s {stat} won't go any higher!"]
        self.modifiers[stat] = min(6, current + change)
        return [f"{self.name}'s {stat} rose!"]

    # ------------------------------------------------------------------
    # Weather-linked abilities. Weather itself is owned by BattleSystem; these
    # only read what this pokemon's ability wants, so the system can apply it.
    # ------------------------------------------------------------------

    def weather_on_switch_in(self) -> str | None:
        """The weather this pokemon's ability summons on entry (Drought → sun),
        or None. Returned as the raw string; BattleSystem maps it to Weather."""
        for effect in self._ability_effects("on_switch_in"):
            if effect.type == "weather" and effect.weather:
                return effect.weather
        return None

    def weather_speed_multiplier(self, weather: str) -> float:
        """Swift Swim / Chlorophyll: a speed multiplier while their weather is up."""
        for effect in self._ability_effects("weather"):
            if effect.type == "speed" and effect.weather == weather:
                return 1 + (effect.change or 0) / 100
        return 1.0

    def weather_heal(self, weather: str) -> list[str]:
        """Rain Dish / Ice Body: heal a little at end of turn in their weather."""
        for effect in self._ability_effects("weather"):
            if (
                effect.type == "heal"
                and effect.weather == weather
                and self.current_hp < self.max_hp
            ):
                healed = max(1, int(self.max_hp * (effect.change or 0) / 100))
                self.current_hp = min(self.max_hp, self.current_hp + healed)
                return [f"{self.name} restored HP with {self.ability_name}!"]
        return []

    def absorbs_weather(self, weather: str) -> bool:
        """Whether this pokemon's ability makes it immune to `weather`'s chip —
        e.g. Ice Body thrives in hail, so it heals instead of taking damage."""
        return any(
            effect.type == "heal" and effect.weather == weather
            for effect in self._ability_effects("weather")
        )

    def on_switch_in(self, opponent: BattlePokemon) -> list[str]:
        messages = []
        for effect in self._ability_effects("on_switch_in"):
            if not self._ability_condition_met(effect):
                continue

            if effect.type == "stat_change":
                target = opponent if effect.target == "enemy" else self
                messages.extend(self._apply_stat_effect(effect, target))
                messages.append(
                    f"{self.name}'s {self.ability_name} took effect!")

            elif effect.type == "status":
                target = opponent if effect.target == "enemy" else self
                applied, message = self._apply_status_effect_ability(
                    effect, target)
                if applied:
                    messages.append(message)

        return messages

    def on_turn_end(self, opponent: BattlePokemon) -> list[str]:
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
                        messages.append(
                            f"{self.name}'s {self.ability_name} cured its {cured}!"
                        )

            elif effect.type == "heal":
                messages.extend(self._heal_from_ability(effect))

        return messages

    @staticmethod
    def _status_from(value) -> StatusEffect | None:
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
        self.status_effect = (
            StatusEffect(self.source.status_condition)
            if self.source.status_condition
            else StatusEffect.NONE
        )

    def sync_to_source(self):
        """Push live battle HP + major status back onto the save member, so a
        bag item (which reads/writes the save) operates on current values."""
        if self.source is None:
            return
        self.source.hp = self.current_hp
        self.source.status_condition = (
            self.status_effect.value if self.status_effect.value else None
        )

    def get_hp_ratio(self) -> float:
        return self.current_hp / self.max_hp

    def gain_exp(self, exp: int) -> ExpGainResult:
        old_stats = self.stats.copy()
        level_before = self.level
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
            moves_to_learn=self._moves_learned_between(
                level_before, self.level),
        )

    # ------------------------------------------------------------------
    # Move learning — the moves list is shared with the source PlayerPokemon,
    # so mutating it here also updates the party member (persists on save).
    # ------------------------------------------------------------------

    def _moves_learned_between(self, old_level: int, new_level: int) -> list[str]:
        """Learnset moves whose level was crossed (old, new], not already known."""
        learned: list[str] = []
        for entry in self.learnset:
            if (
                old_level < entry.level <= new_level
                and not self.knows_move(entry.move)
                and entry.move not in learned
            ):
                learned.append(entry.move)
        return learned

    def knows_move(self, name: str) -> bool:
        return any(m.name.lower() == name.lower() for m in self.moves)

    def has_free_move_slot(self) -> bool:
        return len(self.moves) < MAX_MOVES

    def learn_move(self, name: str, pp: int) -> None:
        self.moves.append(PlayerPokemonMove(name, pp))

    def replace_move(self, index: int, name: str, pp: int) -> str:
        """Overwrite the move at `index`; returns the forgotten move's name."""
        forgotten = self.moves[index].name
        self.moves[index] = PlayerPokemonMove(name, pp)
        return forgotten

    def exp_yield(self):
        return self.progression.exp_yield()

    def get_exp_ratio(self):
        return self.progression.exp_ratio()
