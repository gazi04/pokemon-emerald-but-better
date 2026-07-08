import arcade
import random
from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from src.core.message_service import MessageService
from src.model.static.trainer import Trainer
from src.entities.pokemon_sprites import PokemonSprite
from src.model.battle.battle_pokemon import BattlePokemon
from data.config import Config
from src.ui.battle_ui_manager import BattleUiManager
from src.systems.battle_system import BattleSystem
from src.systems.wild_moveset import select_wild_moves
from src.states.base_view import GameView
from src.enums.battle_state import BattleState

CONFIG = Config.load()


class BattleView(GameView):
    def __init__(
        self,
        overworld_view,
        player_manager: PlayerManager,
        data_loader: DataLoader,
        message_service: MessageService,
        foe_pokemon_name=None,
        foe_pokemon_data=None,
        foe_level=None,
        is_trainer=False,
        trainer_data: Trainer = None,
        npc_id: str = None,
    ):
        super().__init__()

        self.overworld_view = overworld_view
        self.player_manager = player_manager
        self.data_loader = data_loader
        self.message_service = message_service
        self.npc_id = npc_id

        self.ui = BattleUiManager(self.what_happend_after_text)

        self.playerPokemon = self.player_manager.player.pokemon

        lead_pokemon = self.playerPokemon[0]
        player_profile = data_loader.get_pokemon(lead_pokemon.name)
        if player_profile is None:
            raise ValueError(
                f"Player pokemon data for '{lead_pokemon.name}' could not be loaded."
            )

        self.your_battle = BattlePokemon.from_player(
            data_loader.get_ability(lead_pokemon.ability),
            player_profile,
            lead_pokemon,
            held_item=(
                data_loader.get_item(lead_pokemon.held_item)
                if lead_pokemon.held_item
                else None
            ),
        )
        self.your_sprite = PokemonSprite(player_profile, False)

        self.is_trainer = is_trainer
        self.trainer_data = trainer_data
        self.prize_money = 0

        # Move-learning sub-flow state.
        self.learning_move_mode = False       # move menu is picking a move to forget
        self._on_learning_done = None         # called once the learn queue empties

        if not is_trainer:
            if foe_pokemon_data is None or foe_pokemon_name is None or foe_level is None:
                raise ValueError(
                    f"Enemy pokemon data for '{foe_pokemon_name}' cannot be None."
                )
                
            abilities = data_loader.get_ability(random.choice(foe_pokemon_data.abilities))

            self.enemy_battle = BattlePokemon.from_wild(
                foe_pokemon_data,
                foe_pokemon_name,
                foe_level,
                select_wild_moves(foe_pokemon_data, foe_level, data_loader),
                abilities
            )
            self.enemy_sprite = PokemonSprite(foe_pokemon_data, True)
        else:
            first = trainer_data.party[0]
            first_profile = data_loader.get_pokemon(first.name)
            ability = data_loader.get_ability(first.ability)
            if first_profile is None:
                raise ValueError(f"Trainer pokemon '{first.name}' not found in data.")

            self.enemy_battle = BattlePokemon.from_wild(
                first_profile,
                first.name,
                first.level,
                first.moves,
                ability
            )
            self.enemy_sprite = PokemonSprite(first_profile, True)

            self.prize_money = (
                first.level + sum(p.level for p in trainer_data.party)
            ) * 10
            trainer_data.party.pop(0)

        self.player_manager.mark_seen(foe_pokemon_name)

        self.battle_system = BattleSystem(
            self.your_battle,
            self.enemy_battle,
            self.player_manager,
            self.data_loader,
            is_trainer,
            trainer_data,
        )

        self.ui.set_enemy_info(
            self.enemy_battle.name.upper(),
            self.enemy_battle.level,
        )
        self.ui.switch_mode("main")
        # Sprite is freshly built above — back-texture already correct.
        self._refresh_active_pokemon_ui(update_texture=False)

        self.ui.set_transition(
            self.your_sprite,
            self.enemy_sprite,
            is_trainer,
            self.your_battle.name,
            self.enemy_battle.name,
        )

    def update_ui_moves(self):
        moves = self.your_battle.moves
        for i, button in enumerate(self.ui.menu_panel.move_buttons):
            if i < len(moves):
                button.text = moves[i].name.upper()
                button.visible = True
                button.enabled = True
            else:
                button.text = ""
                button.visible = False
                button.enabled = False

    def _refresh_active_pokemon_ui(self, update_texture: bool = True):
        """Refresh name/level + move panel for the active player Pokémon.
        Shared by __init__, switch_turn, and force_switch so they stay in sync;
        the None guard covers a missing move (latent crash if accessed raw)."""
        self.ui.set_player_info(
            self.your_battle.name.upper(),
            self.your_battle.level,
        )
        self.update_ui_moves()
        first_move = self.data_loader.get_move(self.your_battle.moves[0].name)
        if first_move is not None:
            self.ui.menu_panel.update_move_info(
                first_move.type,
                self.your_battle.moves[0].pp,
                first_move.pp,
            )
        else:
            self.ui.menu_panel.update_move_info(
                "Normal", self.your_battle.moves[0].pp, 35
            )
        if update_texture:
            texture = self.data_loader.get_pokemon(
                self.your_battle.name.lower()
            ).sprites.back
            self.your_sprite.set_new_texture(texture)

    def start_turn(self, index):
        self.ui.queue_messages(self.battle_system.turn(index))
        self.ui.switch_mode("dialog")

    def on_item_used(self, item_index: str):
        self.ui.queue_messages(self.battle_system.turn_use_item(item_index))
        self.ui.switch_mode("dialog")

    def on_show_view(self):
        self.message_service.set_box(self.ui.message_box)

    def show_messages(self, messages: list[str]):
        """Show battle text from another view (e.g. bag) — switches to dialog
        mode so the box is visible, then queues via the service."""
        self.ui.switch_mode("dialog")
        self.message_service.show(messages)

    def start_catch_attempt(self, result: dict):
        """Called by BagView after a pokeball is thrown."""
        self.ui.queue_messages(result["messages"])
        self.ui.switch_mode("dialog")

    def switch_turn(self):
        self.battle_system.battle_state = BattleState.SWITCHING

        self.ui.switch_mode("dialog")
        self.ui.queue_messages(self.battle_system.switch_pokemon())

        self._refresh_active_pokemon_ui()

    def what_happend_after_text(self):
        if self.battle_system.battle_state == BattleState.CAUGHT:
            self.battle_system.add_caught_pokemon()
            self.run()
            return

        if self.battle_system.battle_state == BattleState.CURRENTLY_TURN:
            self._on_continue_turn()
        elif self.battle_system.battle_state in (
            BattleState.INTRO,
            BattleState.POST_TURN,
            BattleState.WAITING,
        ):
            self._ending_turn()

        elif self.battle_system.battle_state == BattleState.SWITCHING:
            self.ui.queue_messages(self.battle_system.switch_turn())
            self.ui.switch_mode("dialog")

        elif self.battle_system.battle_state == BattleState.TRAINER_SWITCH:
            self._trainer_give_exp()
        elif self.battle_system.battle_state == BattleState.TRAINER_SENDING:
            self._trainer_send_next_pokemon()
        elif self.battle_system.battle_state == BattleState.PLAYER_FAINTED:
            self._handle_player_fainted()
        elif self.battle_system.battle_state == BattleState.LOST:
            self._end_loss()
        elif self.battle_system.battle_state == BattleState.LEARNING_MOVE:
            self._continue_move_learning()
        elif self.battle_system.battle_state == BattleState.END:
            self._handle_battle_finishing()

    def _handle_player_fainted(self):
        if self.battle_system.has_usable_pokemon():
            # Force the player to choose a replacement.
            self.overlay(
                "pokemon_menu",
                previous_view=self,
                battle_system=self.battle_system,
                forced_switch=True,
            )
        else:
            self._handle_player_loss()

    def force_switch(self):
        """Called by the Pokémon menu after a replacement is chosen post-faint."""
        self.ui.queue_messages(self.battle_system.complete_forced_switch())
        self.ui.switch_mode("dialog")
        # No enemy turn after a forced switch — go back to the main menu.
        self.battle_system.battle_state = BattleState.WAITING

        self._refresh_active_pokemon_ui()

    def _handle_player_loss(self):
        self.battle_system.battle_state = BattleState.LOST
        self.ui.queue_messages(
            [
                "You have no more Pokémon that can fight!",
                "You whited out!",
            ]
        )
        self.ui.switch_mode("dialog")

    def _end_loss(self):
        self.battle_system.save()

        # Whiting out: fully heal the team and send the player to the Poké Center.
        self.player_manager.heal_team()
        self.overworld_view.respawn_at_pokecenter()

        self.close()

    def _on_continue_turn(self):
        messages = self.battle_system.execute_next_action()
        if messages:
            self.ui.queue_messages(messages)
        else:
            self._ending_turn()

    def _ending_turn(self):
        self.battle_system.battle_state = BattleState.WAITING
        arcade.schedule_once(self._reset_to_main_menu, 0.5)

    def _trainer_give_exp(self):
        result = self.battle_system.apply_exp_award()

        if result.leveled_up:
            # Show level-up text, then learn moves, then send the next pokemon.
            self.battle_system.queue_moves_to_learn(result.moves_to_learn)
            self._on_learning_done = self._trainer_send_next_pokemon
            self.battle_system.battle_state = BattleState.LEARNING_MOVE
            self._on_level_up(self.your_battle)
        else:
            self.battle_system.battle_state = BattleState.TRAINER_SENDING
            self._trainer_send_next_pokemon()

    def _trainer_send_next_pokemon(self):
        next_data = self.battle_system.next_trainer_pokemon

        if not next_data:
            messages = ["Trainer was defeated!!!"]
            if self.prize_money > 0:
                messages.append(f"You got ${self.prize_money}!")
            self.ui.queue_messages(messages)
            self.battle_system.battle_state = BattleState.END
            return

        self.set_enemy(next_data.name, next_data.level, next_data.moves)

        self.ui.set_enemy_info(next_data.name.upper(), next_data.level)
        self.ui.queue_messages([f"Trainer sent out {next_data.name}!"])
        self.battle_system.battle_state = BattleState.WAITING

    def set_enemy(self, name: str, level: int, moves: list):
        """Swap the active enemy pokemon, keeping sprite, battle model, and
        battle system in sync. Single entry point so callers can't desync them."""
        profile = self.data_loader.get_pokemon(name)

        self.enemy_sprite.set_new_texture(profile.sprites.front)
        self.enemy_battle = BattlePokemon.from_wild(profile, name, level, moves)
        self.battle_system.enemy_pokemon = self.enemy_battle

    def _handle_battle_finishing(self):
        if self.battle_system.exp <= 0:
            self.run()
            return

        result = self.battle_system.apply_exp_award()

        if result.evolved:
            self._evolution(self.your_battle.name.lower(), result.evolves_to)
        elif result.leveled_up:
            # Level-up text, then any move learning, then leave the battle.
            self.battle_system.queue_moves_to_learn(result.moves_to_learn)
            self._on_learning_done = self.run
            self.battle_system.battle_state = BattleState.LEARNING_MOVE
            self._on_level_up(self.your_battle)
        else:
            self.run()

    # ------------------------------------------------------------------
    # Move learning — message-gated sub-flow. LEARNING_MOVE state re-enters
    # here each time the text box empties until the learn queue is drained.
    # ------------------------------------------------------------------

    def _continue_move_learning(self):
        if self.battle_system.current_learning_move() is not None:
            # A "needs replace" prompt just finished — let the player pick.
            self._open_forget_selector()
        else:
            self._process_next_move_learn()

    def _process_next_move_learn(self):
        outcome = self.battle_system.next_move_to_learn()
        if outcome is None:
            done = self._on_learning_done or self.run
            self._on_learning_done = None
            done()
            return

        self.battle_system.battle_state = BattleState.LEARNING_MOVE
        self.ui.queue_messages(outcome["messages"])
        self.ui.switch_mode("dialog")

    def _open_forget_selector(self):
        """Reuse the move menu to choose which move to forget."""
        self.learning_move_mode = True
        self.update_ui_moves()
        self.ui.menu_panel.selection_index = 0
        self.ui.switch_mode("moves")
        self.move_hover(0)

    def _forget_move(self, index: int):
        self.learning_move_mode = False
        messages = self.battle_system.replace_learned_move(index)
        self.update_ui_moves()
        self.battle_system.battle_state = BattleState.LEARNING_MOVE
        self.ui.queue_messages(messages)
        self.ui.switch_mode("dialog")

    def _cancel_learn_move(self):
        self.learning_move_mode = False
        messages = self.battle_system.skip_learned_move()
        self.battle_system.battle_state = BattleState.LEARNING_MOVE
        self.ui.queue_messages(messages)
        self.ui.switch_mode("dialog")

    def _on_level_up(self, pokemon: BattlePokemon):
        self.ui.set_player_info(
            pokemon.name.upper(),
            pokemon.level,
        )
        self.ui.manager.trigger_render()
        self.ui.queue_messages(
            [
                f"{pokemon.name} has leveled up!!!",
                f"Now {pokemon.name} is {pokemon.level} lvl!!!",
            ]
        )

    def _evolution(self, base_pokemon: str, to: str):
        self.battle_system.has_evolved = True
        self.battle_system.save()
        # Ask the Director to swap to the Evolution view
        self.swap("evolving", pokemon=base_pokemon, evolved_pokemon=to)

    def _reset_to_main_menu(self, dt):
        self.ui.switch_mode("main")
        self.ui.message_box.reset_prompt(f"What will {self.your_battle.name} do?")

    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        self.ui.draw()
        self.enemy_sprite.draw()
        self.your_sprite.draw()
        self.ui.draw_hp_bar(self.your_battle.get_hp_ratio(), "player")
        self.ui.draw_exp_bar(self.your_battle.get_exp_ratio())
        self.ui.draw_hp_bar(self.enemy_battle.get_hp_ratio(), "enemy")
        self.ui.draw_status(self.your_battle.status_effect, "player")
        self.ui.draw_status(self.enemy_battle.status_effect, "enemy")

    def on_update(self, delta_time):
        self.ui.update(delta_time)

    def on_key_press(self, symbol: int, modifiers: int):
        if self.ui.active_component == "main":
            current_list = self.ui.menu_panel.main_buttons
            num_buttons = len(current_list)
        elif self.ui.active_component == "moves":
            current_list = self.ui.menu_panel.move_buttons
            num_buttons = len(self.your_battle.moves)
        else:
            return

        if self.is_pressed(CONFIG.controls.up, symbol):
            if num_buttons > 2:
                self.ui.menu_panel.selection_index = (
                    self.ui.menu_panel.selection_index - 2
                ) % num_buttons
            if self.ui.active_component == "moves":
                self.move_hover(self.ui.menu_panel.selection_index)

        elif self.is_pressed(CONFIG.controls.down, symbol):
            if num_buttons > 2:
                self.ui.menu_panel.selection_index = (
                    self.ui.menu_panel.selection_index + 2
                ) % num_buttons
            if self.ui.active_component == "moves":
                self.move_hover(self.ui.menu_panel.selection_index)

        elif self.is_pressed(CONFIG.controls.left, symbol):
            self.ui.menu_panel.selection_index = (
                self.ui.menu_panel.selection_index - 1
            ) % num_buttons
            if self.ui.active_component == "moves":
                self.move_hover(self.ui.menu_panel.selection_index)

        elif self.is_pressed(CONFIG.controls.right, symbol):
            self.ui.menu_panel.selection_index = (
                self.ui.menu_panel.selection_index + 1
            ) % num_buttons
            if self.ui.active_component == "moves":
                self.move_hover(self.ui.menu_panel.selection_index)

        elif self.is_pressed(CONFIG.controls.interact, symbol):
            if self.ui.active_component == "main":
                if self.ui.menu_panel.selection_index == 0:
                    self.ui.switch_mode("moves")
                elif self.ui.menu_panel.selection_index == 1:
                    # Ask the Director to overlay the Bag
                    self.overlay(
                        "bag", previous_view=self, battle_system=self.battle_system
                    )
                elif self.ui.menu_panel.selection_index == 2:
                    # Ask the Director to overlay the Pokémon menu
                    self.overlay(
                        "pokemon_menu",
                        previous_view=self,
                        battle_system=self.battle_system,
                    )
                elif self.ui.menu_panel.selection_index == 3:
                    if not self.is_trainer:
                        self.run()
                    else:
                        self.ui.queue_messages(["You cant run away from trainers!"])
                        self.ui.switch_mode("dialog")
                        arcade.schedule_once(self._reset_to_main_menu, 2)

            elif self.ui.active_component == "moves":
                if self.learning_move_mode:
                    self._forget_move(self.ui.menu_panel.selection_index)
                else:
                    self.start_turn(self.ui.menu_panel.selection_index)

        elif self.is_pressed(CONFIG.controls.cancel, symbol):
            if self.ui.active_component == "moves":
                if self.learning_move_mode:
                    self._cancel_learn_move()
                else:
                    self.ui.switch_mode("main")

    def move_hover(self, index):
        if index is not None and index < len(self.your_battle.moves):
            move_name = self.your_battle.moves[index].name
            move = self.data_loader.get_move(move_name)

            if move is not None:
                self.ui.menu_panel.update_move_info(
                    move.type,
                    self.your_battle.moves[index].pp,
                    move.pp,
                )

    def run(self):
        self.battle_system.save()

        if self.is_trainer:
            # Trainer battles can't be fled, so reaching here means victory.
            if self.prize_money > 0:
                self.player_manager.add_money(self.prize_money)

            if self.npc_id:
                self.player_manager.npc_manager.mark_defeated(self.npc_id)
                npc = self.data_loader.npc_dialog.get(self.npc_id)
                if npc and npc.has_state("after_victory"):
                    # Show the post-battle dialog instead of going straight back.
                    self.overlay(
                        "dialog",
                        npc_id=self.npc_id,
                        state="after_victory",
                        action="end",
                    )
                    return

        # Tell the Director we are done — it will return to the Overworld
        self.close()
