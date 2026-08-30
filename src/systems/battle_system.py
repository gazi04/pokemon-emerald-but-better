import random

from src.model.battle.battle_pokemon import BattlePokemon
from src.core.player_manager import PlayerManager
from src.core.data_loader import DataLoader
from src.core.combat_calculator import calculate_damage
from src.core.catch_calculator import calc_catch_probability
from src.core.event_bus import global_bus
from src.core.events import HpChangedEvent
from src.enums.battle_state import BattleState
from src.enums.stat import Stat
from src.enums.effect_type import EffectType
from src.enums.weather import Weather
from src.model.battle.weather_state import WeatherState
from src.model.battle.exp_gain_result import ExpGainResult
from src.model.save.player import PlayerPokemon
from src.model.static.item import ItemSpecies
from src.model.static.trainer import Trainer, TrainerPokemon
from src.model.static.pokemon import PokemonMove
from src.systems.enemy_ai import EnemyAI
from src.constants import CHANCE_TO_GET_ITEM, ITEMS_FROM_PICK_UP


class BattleSystem:
    def __init__(
        self,
        your_pokemon: BattlePokemon,
        enemy_pokemon: BattlePokemon,
        player_manager: PlayerManager,
        data_loader: DataLoader,
        is_trainer=False,
        trainer_data: Trainer | None = None,
    ):
        self.your_pokemon = your_pokemon
        self.enemy_pokemon = enemy_pokemon
        self.player_manager = player_manager
        self.data_loader = data_loader

        self.turn_queue: list[tuple[str, int, str | int | None]] = []
        self.battle_state = BattleState.INTRO
        self.exp = 0
        self.has_evolved = False

        # Battle-wide weather (clear until a move or ability summons it).
        self.weather = WeatherState()

        self._last_player_move = ""

        # Move-learning queue for the active pokemon after a level-up.
        self._learn_queue: list[str] = []
        self._pending_learn: str | None = None

        self.ai = EnemyAI(1, data_loader)

        self.is_trainer = is_trainer
        self.trainer_party = trainer_data.party if trainer_data else []
        self.next_trainer_pokemon: TrainerPokemon | None = None

        # Party member the queued item was used on; None = the active pokemon.
        self._item_target_name: str | None = None

    def start_battle(self) -> list[str]:
        """Fire the active Pokémon's entry effects (currently weather-setting
        abilities like Drought/Drizzle). The slower Pokémon activates last, so
        its weather wins — matching the games. Called once by the view on intro.
        """
        messages: list[str] = []
        by_speed = sorted(
            (self.enemy_pokemon, self.your_pokemon),
            key=lambda p: p.get_stat(Stat.SPEED),
            reverse=True,
        )
        for pokemon in by_speed:
            summoned = pokemon.weather_on_switch_in()
            if summoned:
                messages.append(f"{pokemon.name}'s {pokemon.ability_name} kicked in!")
                messages.extend(self.weather.set(Weather(summoned)))
        return messages

    def battle_ended(self) -> list[str]:
        messages = []

        if self.your_pokemon.ability is None:
            return []

        if (
            self.your_pokemon.ability.name.lower() == "pick up"
            and random.random() <= CHANCE_TO_GET_ITEM
        ):
            item = random.choice(ITEMS_FROM_PICK_UP)

            if item:
                self.player_manager.add_item(item)
                messages.append(f"Your got {item.upper()}!!!")

        return messages

    def _weather_speed(self, pokemon: BattlePokemon) -> int:
        """Speed for turn order, including Swift Swim / Chlorophyll in weather."""
        base = pokemon.get_stat(Stat.SPEED)
        return round(base * pokemon.weather_speed_multiplier(self.weather.kind))

    def turn(self, move_index: int) -> list[str]:
        self.battle_state = BattleState.CURRENTLY_TURN
        enemy_move_index = self.ai.select_move(self.enemy_pokemon, self.your_pokemon)

        player_move_name = self.your_pokemon.moves[move_index].name
        player_move_data = self.data_loader.get_move(player_move_name)
        if player_move_data is None:
            raise ValueError(f"Move data for '{player_move_name}' could not be loaded.")

        if enemy_move_index is None:
            self.turn_queue = [("player", move_index, None)]
            return self.execute_next_action()

        enemy_move_name = self.enemy_pokemon.moves[enemy_move_index].name
        enemy_move_data = self.data_loader.get_move(enemy_move_name)
        if enemy_move_data is None:
            raise ValueError(f"Move data for '{enemy_move_name}' could not be loaded.")

        player_priority = player_move_data.priority
        enemy_priority = enemy_move_data.priority

        if self._player_moves_first(
            self._weather_speed(self.your_pokemon),
            player_priority,
            self._weather_speed(self.enemy_pokemon),
            enemy_priority,
        ):
            self.turn_queue = [
                ("player", move_index, None),
                ("enemy", enemy_move_index, None),
            ]
        else:
            self.turn_queue = [
                ("enemy", enemy_move_index, None),
                ("player", move_index, None),
            ]

        return self.execute_next_action()

    def _player_moves_first(
        self,
        player_speed: int,
        player_priority: int,
        enemy_speed: int,
        enemy_priority: int,
    ) -> bool:
        return player_priority > enemy_priority or (
            player_priority == enemy_priority and player_speed >= enemy_speed
        )

    def turn_use_item(
        self, item_index: str, target_name: str | None = None
    ) -> list[str]:
        """Spend the turn on an item. `target_name` is the party member it was
        used on; None means the active pokemon.
        """
        self.battle_state = BattleState.CURRENTLY_TURN
        self._item_target_name = target_name
        enemy_move_index = self.ai.select_move(self.enemy_pokemon, self.your_pokemon)
        self.turn_queue = [("player", -1, item_index)]
        if enemy_move_index is not None:
            self.turn_queue.append(("enemy", enemy_move_index, None))
        return self.execute_next_action()

    def switch_turn(self) -> list[str]:
        self.battle_state = BattleState.CURRENTLY_TURN
        enemy_move_index = self.ai.select_move(self.enemy_pokemon, self.your_pokemon)

        self.turn_queue = (
            [("enemy", enemy_move_index, None)] if enemy_move_index is not None else []
        )
        return self.execute_next_action()

    def switch_pokemon(self) -> list[str]:
        if self.player_manager.player is None:
            raise RuntimeError(
                "BattleSystem.switch_pokemon requires a loaded player save"
            )
        pokemon = self.player_manager.player.pokemon[0]

        pokemon_profile = self.data_loader.get_pokemon(pokemon.name)
        if pokemon_profile is None:
            raise ValueError(f"Pokemon data for '{pokemon.name}' could not be loaded.")

        ability = self.data_loader.get_ability(pokemon.ability)
        if ability is None:
            raise ValueError(
                f"Ability data for '{pokemon.ability}' could not be loaded."
            )

        if pokemon.hp <= 0:
            return [f"{pokemon.name} is unable to battle!"]

        messages = [f"Go {pokemon.name}!"]

        held_item = (
            self.data_loader.get_item(pokemon.held_item) if pokemon.held_item else None
        )
        self.your_pokemon.switching_pokemon(
            pokemon, ability, pokemon_profile, held_item
        )

        messages.extend(self.your_pokemon.on_switch_in(self.enemy_pokemon))
        return messages

    def execute_next_action(self) -> list[str]:
        if not self.turn_queue:
            return self.post_turn()

        messages = []
        attacker_key, move_index, item_index = self.turn_queue.pop(0)

        if attacker_key == "player" and self.your_pokemon.current_hp > 0:
            # No item this action (None or a negative sentinel) -> it's a move.
            # A real item can sit at index 0, so a truthiness check is wrong.
            if item_index is None or (isinstance(item_index, int) and item_index < 0):
                messages.extend(
                    self._dispatch_move(
                        self.your_pokemon, self.enemy_pokemon, move_index, "enemy"
                    )
                )
            else:
                messages.extend(self._apply_item_to_pokemon(item_index))

        elif attacker_key == "enemy" and self.enemy_pokemon.current_hp > 0:
            messages.extend(
                self._dispatch_move(
                    self.enemy_pokemon, self.your_pokemon, move_index, "player"
                )
            )

        if self.your_pokemon.current_hp <= 0 or self.enemy_pokemon.current_hp <= 0:
            self.turn_queue.clear()

        return messages

    def _dispatch_move(
        self,
        attacker: BattlePokemon,
        defender: BattlePokemon,
        move_index: int,
        defender_label: str,
    ) -> list[str]:
        """Routes to single-hit or multi-hit execution based on move data."""
        move_name = attacker.moves[move_index].name
        move_data = self.data_loader.get_move(move_name)
        if move_data is None:
            raise ValueError(f"Move data for '{move_name}' could not be loaded.")

        if move_data.multi_hit:
            return self._execute_move_multiple_times(
                attacker, defender, move_index, defender_label
            )
        return self._execute_move(attacker, defender, move_index, defender_label)

    def _execute_move_multiple_times(
        self,
        attacker: BattlePokemon,
        defender: BattlePokemon,
        move_index: int,
        defender_label: str,
    ) -> list[str]:
        move_name = attacker.moves[move_index].name
        move_data = self.data_loader.get_move(move_name)
        if move_data is None:
            raise ValueError(f"Move data for '{move_name}' could not be loaded.")
        if move_data.multi_hit is None:
            raise ValueError(f"Move '{move_name}' has no multi_hit range defined.")
        min_hits, max_hits = move_data.multi_hit
        times = random.randint(min_hits, max_hits)

        messages = []
        hits_landed = 0

        for hit_number in range(1, times + 1):
            hit_messages = self._execute_move(
                attacker,
                defender,
                move_index,
                defender_label,
                announce=(hit_number == 1),
            )
            messages.extend(hit_messages)
            hits_landed += 1

            if defender.current_hp <= 0:
                break
        if hits_landed > 1:
            messages.append(f"Hit {hits_landed} time(s)!")

        return messages

    def _execute_move(
        self,
        attacker: BattlePokemon,
        defender: BattlePokemon,
        move_index: int,
        defender_label: str,
        announce: bool = True,
    ) -> list[str]:
        move_name = attacker.moves[move_index].name
        move_data = self.data_loader.get_move(move_name)
        if move_data is None:
            raise ValueError(f"Move data for '{move_name}' could not be loaded.")
        messages = []

        if announce:
            prefix = "" if attacker == self.your_pokemon else "Foe "
            messages.append(f"{prefix}{attacker.name} used {move_data.name}!")

            # Status / PP checks
            status_messages, can_move = attacker.check_can_move(move_index)
            messages.extend(status_messages)
            if not can_move:
                return messages

            failure_message = self._check_move_condition(move_data, attacker)
            if failure_message:
                messages.append(failure_message)
                return messages

        if defender.is_protected:
            messages.append(f"{defender.name} protected itself!")
            return messages

        # Ability: defender immunity (e.g. Levitate vs Ground) — absolute, so
        # short-circuit before accuracy/damage are even rolled.
        immunity_message = defender.immunity_to(move_data)
        if immunity_message:
            messages.append(immunity_message)
            return messages

        # Ability: attacker on-attack power boost (e.g. Blaze at low HP).
        attack_multiplier, ability_attack_messages = attacker.ability_attack_multiplier(
            move_data
        )

        # Pure damage calculation — no side effects
        result = calculate_damage(
            attacker_level=attacker.level,
            attacker_stats=attacker.stats,
            attacker_types=attacker.types,
            attacker_modifiers=attacker.modifiers,
            attacker_status=attacker.status_effect,
            move_data=move_data,
            defender_stats=defender.stats,
            defender_types=defender.types,
            defender_modifiers=defender.modifiers,
            crit_modifier=attacker.modifiers.get(Stat.CRITS, 0) + move_data.crit,
            type_chart=self.data_loader.types,
            weather_multiplier=self.weather.damage_multiplier(move_data.type),
        )

        messages.extend(result.messages)

        if result.is_miss:
            return messages

        # Apply damage (attacker ability boost + held-item boost, e.g. Life Orb,
        # type boosters, Choice Band/Specs).
        item_multiplier = attacker.item_attack_multiplier(move_data)
        damage = round(result.damage * attack_multiplier * item_multiplier)
        hp_before = defender.current_hp
        if damage > 0:
            defender.take_damage(damage)
            messages.extend(ability_attack_messages)

        # Apply move effects (stat changes, status conditions) — state mutation
        effect_messages = attacker.execute_effects(move_data, defender)
        messages.extend(effect_messages)

        # Weather-summoning moves (Rain Dance, Sunny Day, Sandstorm, Hail).
        messages.extend(self._apply_move_weather(move_data))

        # Ability + held-item on-hit reactions (Static, Rocky Helmet), and the
        # attacker's own Life Orb recoil — only when a hit actually landed.
        messages.extend(defender.on_hit(attacker, move_data))
        if damage > 0:
            messages.extend(defender.item_on_hit(attacker, move_data))
            messages.extend(attacker.item_recoil_self(move_data))

        # Held-berry reactions to the new state (Lum on status, pinch berries on HP)
        messages.extend(defender.consume_berry_on_status())
        messages.extend(attacker.consume_berry_on_status())
        messages.extend(defender.consume_berry_on_hp())
        messages.extend(attacker.consume_berry_on_hp())

        # Publish HP change for UI bar update
        self._publish_hp_change(defender_label, hp_before, defender)

        self._last_player_move = move_data.name

        return messages

    def _apply_move_weather(self, move_data: PokemonMove) -> list[str]:
        """Summon weather from a move's `weather` effect, if it has one."""
        messages: list[str] = []
        for effect in move_data.effects:
            if effect.type == EffectType.WEATHER and effect.weather:
                messages.extend(self.weather.set(Weather(effect.weather)))
        return messages

    def _check_move_condition(
        self, move_data: PokemonMove, attacker: BattlePokemon
    ) -> str | None:
        """Returns a failure message if the move's condition isn't met, else None."""
        condition = move_data.condition
        if not condition:
            return None

        if condition == "first_turn_only" and not attacker.is_first_turn:
            return f"But {move_data.name} failed!"

        if condition == "not_consecutive" and self._last_player_move == move_data.name:
            return f"But {move_data.name} failed!"

        return None

    def sync_active_to_save(self) -> None:
        """Push the active pokemon's live HP/status to the save so a bag item
        (which operates on the save) heals/cures from current values."""
        self.your_pokemon.sync_to_source()

    def _apply_item_to_pokemon(self, item_index: str | int) -> list[str]:
        """Reflect a bag item's effect on the battle model.

        The bag has already written the save for the targeted party member. Only
        the *active* pokemon has a battle model and an HP bar, so a benched target
        gets the message and nothing else.
        """
        target_name = self._item_target_name

        if target_name and target_name.lower() != self.your_pokemon.name.lower():
            return [f"{target_name.capitalize()} used {item_index}!"]

        hp_before = self.your_pokemon.current_hp
        self.your_pokemon.sync_from_source()

        if self.your_pokemon.current_hp != hp_before:
            self._publish_hp_change("player", hp_before, self.your_pokemon)

        return [f"{self.your_pokemon.name} used {item_index}!"]

    def post_turn(self) -> list[str]:
        messages = []
        hp_before_yours = self.your_pokemon.current_hp
        hp_before_enemy = self.enemy_pokemon.current_hp

        messages.extend(self.your_pokemon.after_a_turn())
        messages.extend(self.enemy_pokemon.after_a_turn())

        messages.extend(self.your_pokemon.on_turn_end(self.enemy_pokemon))
        messages.extend(self.enemy_pokemon.on_turn_end(self.your_pokemon))

        # Held items: Leftovers heal, then pinch berries if end-of-turn damage
        # (poison/burn) dropped the holder to its berry threshold.
        messages.extend(self.your_pokemon.item_turn_end())
        messages.extend(self.enemy_pokemon.item_turn_end())
        messages.extend(self.your_pokemon.consume_berry_on_hp())
        messages.extend(self.enemy_pokemon.consume_berry_on_hp())

        # Weather: heal abilities, sandstorm/hail chip, then the duration tick.
        # Runs before the HP-change publishes below so the bars reflect it, and
        # before the faint checks so weather can KO.
        messages.extend(self._apply_weather_end_of_turn())

        if self.your_pokemon.current_hp != hp_before_yours:
            self._publish_hp_change("player", hp_before_yours, self.your_pokemon)
        if self.enemy_pokemon.current_hp != hp_before_enemy:
            self._publish_hp_change("enemy", hp_before_enemy, self.enemy_pokemon)

        if self.your_pokemon.current_hp <= 0:
            messages.extend(self.pokemon_death(self.your_pokemon))
            return messages
        if self.enemy_pokemon.current_hp <= 0:
            messages.extend(self.pokemon_death(self.enemy_pokemon))
            return messages

        self.battle_state = (
            BattleState.POST_TURN if len(messages) > 0 else BattleState.WAITING
        )
        return messages

    def _apply_weather_end_of_turn(self) -> list[str]:
        """Weather's per-turn effects on both active Pokémon, then its countdown.

        Heal abilities (Rain Dish/Ice Body) first, then sandstorm/hail chip on
        anything not immune. HP changes are published by post_turn's net-change
        check, so this only mutates and messages.
        """
        if not self.weather.is_active:
            return []

        messages: list[str] = []
        for pokemon in (self.your_pokemon, self.enemy_pokemon):
            if pokemon.current_hp <= 0:
                continue

            messages.extend(pokemon.weather_heal(self.weather.kind))

            takes_chip = self.weather.damages(
                pokemon.types
            ) and not pokemon.absorbs_weather(self.weather.kind)
            if takes_chip:
                pokemon.take_damage(self.weather.residual_damage(pokemon.max_hp))
                messages.append(self.weather.residual_message(pokemon.name))

        messages.extend(self.weather.tick())
        return [m for m in messages if m]

    def pokemon_death(self, died_pokemon: BattlePokemon) -> list[str]:
        messages = []

        if died_pokemon.is_enemy:
            self.battle_state = BattleState.END
            self.exp = died_pokemon.exp_yield()
            messages.extend(
                [
                    f"{self.enemy_pokemon.name} fainted!",
                    f"{self.your_pokemon.name} gained {self.exp} EXP. Points!",
                ]
            )

            if self.is_trainer and self.trainer_party:
                self.next_trainer_pokemon = self.trainer_party.pop(0)
                self.battle_state = BattleState.TRAINER_SWITCH
        else:
            # Persist the faint to the team member (through the single mutation
            # door, not a raw save-layer write) so the bench/active HP is accurate
            # when we decide between switching and losing. save() only persists the
            # active pokemon, so a fainted-then-switched-out mon must be saved here.
            if self.your_pokemon.source is not None:
                self.player_manager.update_pokemon_hp(
                    self.your_pokemon.name.lower(), self.your_pokemon.current_hp
                )
            self.battle_state = BattleState.PLAYER_FAINTED
            messages.append(f"{self.your_pokemon.name} fainted!")

        return messages

    def has_usable_pokemon(self) -> bool:
        """True if the player still has at least one Pokémon that can fight."""
        if self.player_manager.player is None:
            raise RuntimeError(
                "BattleSystem.has_usable_pokemon requires a loaded player save"
            )
        return any(p.hp > 0 for p in self.player_manager.player.pokemon)

    def complete_forced_switch(self) -> list[str]:
        """
        Bring in the replacement chosen after a faint. The team list has
        already been reordered so the new active is at index 0. No enemy turn
        follows a forced switch.
        """
        messages = []

        if self.player_manager.player is None:
            raise RuntimeError(
                "BattleSystem.complete_forced_switch requires a loaded player save"
            )
        pokemon = self.player_manager.player.pokemon[0]

        profile = self.data_loader.get_pokemon(pokemon.name)
        if profile is None:
            raise ValueError(f"Pokemon data for '{pokemon.name}' could not be loaded.")

        ability = self.data_loader.get_ability(pokemon.ability)
        if ability is None:
            raise ValueError(
                f"Ability data for '{pokemon.ability}' could not be loaded."
            )

        held_item = (
            self.data_loader.get_item(pokemon.held_item) if pokemon.held_item else None
        )
        self.your_pokemon.switching_pokemon(pokemon, ability, profile, held_item)

        messages.extend(self.your_pokemon.on_switch_in(self.enemy_pokemon))
        messages.append(f"Go {pokemon.name}!")

        return messages

    def apply_exp_award(self) -> ExpGainResult:
        """Award pending exp to the active Pokémon and clear it. Returns the
        ExpGainResult so the view can react (level-up / evolve / nothing)
        without mutating the model itself."""
        result = self.your_pokemon.gain_exp(self.exp)
        self.exp = 0
        return result

    # ------------------------------------------------------------------
    # Move learning after a level-up. The view drives this like the other
    # message-gated sub-flows: queue the names, then pump next_move_to_learn()
    # until it returns None, handling a replacement prompt in between.
    # ------------------------------------------------------------------

    def queue_moves_to_learn(self, move_names: list[str]) -> None:
        self._learn_queue.extend(move_names)

    def has_pending_learn(self) -> bool:
        return bool(self._learn_queue) or self._pending_learn is not None

    def current_learning_move(self) -> str | None:
        """The move awaiting a forget-a-move choice, or None."""
        return self._pending_learn

    def next_move_to_learn(self) -> dict | None:
        """Advance the learn queue.
        Returns None when done, {"type": "learned", ...} when a free slot let the
        move be learned outright, or {"type": "needs_replace", ...} when the
        moveset is full and the player must pick a move to forget.
        """
        if not self._learn_queue:
            return None

        name = self._learn_queue.pop(0)
        if self.your_pokemon.knows_move(name):
            return self.next_move_to_learn()  # already knows it — skip

        move = self.data_loader.get_move(name)
        display = (move.name if move else name).capitalize()

        if self.your_pokemon.has_free_move_slot():
            self.your_pokemon.learn_move(name, move.pp if move else 0)
            return {
                "type": "learned",
                "messages": [f"{self.your_pokemon.name} learned {display}!"],
            }

        self._pending_learn = name
        return {
            "type": "needs_replace",
            "move": display,
            "messages": [
                f"{self.your_pokemon.name} wants to learn {display}.",
                f"But {self.your_pokemon.name} already knows four moves.",
                f"Forget a move to make room for {display}?",
            ],
        }

    def replace_learned_move(self, index: int) -> list[str]:
        """Forget the move at `index` and learn the pending one."""
        if self._pending_learn is None:
            raise RuntimeError(
                "replace_learned_move() called with no pending learn; "
                "caller must check has_pending_learn()/current_learning_move() first"
            )
        name = self._pending_learn
        self._pending_learn = None
        move = self.data_loader.get_move(name)
        display = (move.name if move else name).capitalize()
        forgotten = self.your_pokemon.replace_move(index, name, move.pp if move else 0)
        return [
            f"{self.your_pokemon.name} forgot {forgotten.capitalize()}...",
            f"...and learned {display}!",
        ]

    def skip_learned_move(self) -> list[str]:
        """Decline to learn the pending move."""
        if self._pending_learn is None:
            raise RuntimeError(
                "skip_learned_move() called with no pending learn; "
                "caller must check has_pending_learn()/current_learning_move() first"
            )
        name = self._pending_learn
        self._pending_learn = None
        move = self.data_loader.get_move(name)
        display = (move.name if move else name).capitalize()
        return [f"{self.your_pokemon.name} did not learn {display}."]

    def add_caught_pokemon(self) -> dict:
        """Add the just-caught enemy to the party (CAUGHT flow).

        Returns the same {"success", "messages"} shape as attempt_catch().
        "messages" is empty on success (nothing extra to show after "Gotcha!");
        a full party sends the catch to storage, which is still a success. Only
        an outright storage failure returns success=False with an explanation.
        """
        enemy = self.enemy_pokemon
        stored = self.player_manager.add_pokemon(
            PlayerPokemon(
                name=enemy.name.lower(),
                hp=enemy.current_hp,
                level=enemy.level,
                exp=0,
                ability=enemy.ability.name.lower() if enemy.ability else "",
                moves=enemy.moves,
                held_item=None,
            )
        )
        if not stored:
            return {
                "success": False,
                "messages": [f"There was no room for {enemy.name}!"],
            }
        return {"success": True, "messages": []}

    def attempt_catch(self, item_data: ItemSpecies) -> dict:
        ball_modifier = 1
        for effect in item_data.effects:
            if effect.type == EffectType.CATCH:
                ball_modifier = effect.catch_rate or 1

        enemy = self.enemy_pokemon
        pokemon_profile = self.data_loader.get_pokemon(enemy.name.lower())
        catch_rate = pokemon_profile.catch_rate if pokemon_profile else 45

        catch_probability = calc_catch_probability(
            catch_rate,
            ball_modifier,
            enemy.current_hp,
            enemy.max_hp,
            enemy.status_effect,
        )

        if random.random() < catch_probability:
            self.battle_state = BattleState.CAUGHT
            return {
                "success": True,
                "messages": [
                    "You threw a Pokeball!",
                    f"Gotcha! {enemy.name} was caught!",
                ],
            }
        else:
            if self.enemy_pokemon.moves:
                enemy_move_index = random.randint(0, len(self.enemy_pokemon.moves) - 1)
                self.turn_queue = [("enemy", enemy_move_index, -1)]
            else:
                self.turn_queue = []
            self.battle_state = BattleState.CURRENTLY_TURN
            return {
                "success": False,
                "messages": [
                    "You threw a Pokeball!",
                    f"Oh no! {enemy.name} broke free!",
                ],
            }

    def save(self):
        # Persistence is owned by the PlayerManager Facade, not combat code.
        self.player_manager.persist_active_pokemon(self.your_pokemon, self.has_evolved)

    def can_run(self) -> bool:
        if self.is_trainer:
            return False

        if self.your_pokemon.ability_name.lower() == "tun away":
            return True

        return self.your_pokemon.level >= self.enemy_pokemon.level

    def _publish_hp_change(self, target: str, hp_before: int, pokemon: BattlePokemon):
        global_bus.publish(
            HpChangedEvent(
                target=target,
                old_hp=hp_before,
                new_hp=pokemon.current_hp,
                max_hp=pokemon.max_hp,
            )
        )
