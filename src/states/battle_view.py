import arcade
from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from src.model.save.player import PlayerPokemon, PlayerPokemonMove
from src.model.static.trainer import Trainer
from src.entities.pokemon_sprites import PokemonSprite
from src.model.battle.battle_pokemon import BattlePokemon
from data.config import Config
from src.ui.battle_ui_manager import BattleUiManager
from src.systems.battle_system import BattleSystem
from src.core.event_bus import global_bus
from src.core.events import CloseViewEvent, OverlayViewEvent, SwapViewEvent
from src.enums.battle_state import BattleState

CONFIG = Config.load()


class BattleView(arcade.View):
    def __init__(
        self,
        overworld_view,
        player_manager: PlayerManager,
        data_loader: DataLoader,
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
        self.npc_id = npc_id

        self.ui = BattleUiManager(self.what_happend_after_text)

        self.playerPokemon = self.player_manager.player.pokemon

        player_profile = data_loader.get_pokemon(self.playerPokemon[0].name)
        if player_profile is None:
            raise ValueError(
                f"Player pokemon data for '{self.playerPokemon[0].name}' could not be loaded."
            )

        self.your_battle = BattlePokemon.from_player(player_profile, self.playerPokemon[0])
        self.your_sprite = PokemonSprite(player_profile, False)

        self.is_trainer = is_trainer
        self.trainer_data = trainer_data
        self.prize_money = 0

        if not is_trainer:
            if foe_pokemon_data is None:
                raise ValueError(
                    f"Enemy pokemon data for '{foe_pokemon_name}' cannot be None."
                )

            self.enemy_battle = BattlePokemon.from_wild(
                foe_pokemon_data,
                foe_pokemon_name,
                foe_level,
                [PlayerPokemonMove("tackle", 35)],
            )
            self.enemy_sprite = PokemonSprite(foe_pokemon_data, True)
        else:
            first = trainer_data.party[0]
            first_profile = data_loader.get_pokemon(first.name)
            if first_profile is None:
                raise ValueError(f"Trainer pokemon '{first.name}' not found in data.")

            self.enemy_battle = BattlePokemon.from_wild(
                first_profile,
                first.name,
                first.level,
                first.moves,
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

        self.ui.set_player_info(
            self.your_battle.name.upper(),
            self.your_battle.level,
        )
        self.ui.set_enemy_info(
            self.enemy_battle.name.upper(),
            self.enemy_battle.level,
        )
        self.ui.switch_mode("main")
        self.update_ui_moves()

        first_move = data_loader.get_move(self.your_battle.moves[0].name)
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

    def start_turn(self, index):
        self.ui.queue_messages(self.battle_system.turn(index))
        self.ui.switch_mode("dialog")

    def on_item_used(self, item_index: int):
        self.ui.queue_messages(self.battle_system.turn_use_item(item_index))
        self.ui.switch_mode("dialog")

    def start_catch_attempt(self, result: dict):
        """Called by BagView after a pokeball is thrown."""
        self.ui.queue_messages(result["messages"])
        self.ui.switch_mode("dialog")

    def switch_turn(self):
        self.battle_system.battle_state = BattleState.SWITCHING

        self.ui.switch_mode("dialog")
        self.ui.queue_messages(self.battle_system.switch_pokemon())

        self.ui.set_player_info(
            self.your_battle.name.upper(),
            self.your_battle.level,
        )
        self.update_ui_moves()
        first_move = self.data_loader.get_move(self.your_battle.moves[0].name)
        self.ui.menu_panel.update_move_info(
            first_move.type,
            self.your_battle.moves[0].pp,
            first_move.pp,
        )

        texture = self.data_loader.get_pokemon(self.your_battle.name.lower()).sprites.back
        self.your_sprite.set_new_texture(texture)

    def what_happend_after_text(self):
        if self.battle_system.battle_state == BattleState.CAUGHT:
            enemy = self.battle_system.enemy_pokemon
            self.player_manager.add_pokemon(
                PlayerPokemon(
                    name=enemy.name.lower(),
                    hp=enemy.current_hp,
                    level=enemy.level,
                    exp=0,
                    moves=enemy.moves,
                )
            )
            self.run()
            return

        if self.battle_system.battle_state == BattleState.CURRENTLY_TURN:
            self._on_continue_turn()
        elif self.battle_system.battle_state in (BattleState.INTRO, BattleState.POST_TURN, BattleState.WAITING):
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
        elif self.battle_system.battle_state == BattleState.END:
            self._handle_battle_finishing()

    def _handle_player_fainted(self):
        if self.battle_system.has_usable_pokemon():
            # Force the player to choose a replacement.
            global_bus.publish(
                OverlayViewEvent(
                    target="pokemon_menu",
                    payload={
                        "previous_view": self,
                        "data_loader": self.data_loader,
                        "battle_system": self.battle_system,
                        "forced_switch": True,
                    },
                )
            )
        else:
            self._handle_player_loss()

    def force_switch(self):
        """Called by the Pokémon menu after a replacement is chosen post-faint."""
        self.ui.queue_messages(self.battle_system.complete_forced_switch())
        self.ui.switch_mode("dialog")
        # No enemy turn after a forced switch — go back to the main menu.
        self.battle_system.battle_state = BattleState.WAITING

        self.ui.set_player_info(
            self.your_battle.name.upper(),
            self.your_battle.level,
        )
        self.update_ui_moves()
        first_move = self.data_loader.get_move(self.your_battle.moves[0].name)
        self.ui.menu_panel.update_move_info(
            first_move.type,
            self.your_battle.moves[0].pp,
            first_move.pp,
        )

        texture = self.data_loader.get_pokemon(self.your_battle.name.lower()).sprites.back
        self.your_sprite.set_new_texture(texture)

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

        global_bus.publish(CloseViewEvent())

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
        result = self.your_battle.gain_exp(self.battle_system.exp)
        self.battle_system.exp = 0
        self.battle_system.battle_state = BattleState.TRAINER_SENDING

        if result.leveled_up:
            self._on_level_up(self.your_battle)
        else:
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

        result = self.your_battle.gain_exp(self.battle_system.exp)
        self.battle_system.exp = 0

        if result.evolved:
            self._evolution(self.your_battle.name.lower(), result.evolves_to)
        elif result.leveled_up:
            self._on_level_up(self.your_battle)
        else:
            self.run()

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
        global_bus.publish(
            SwapViewEvent(
                target="evolving",
                payload={
                    "pokemon": base_pokemon,
                    "evolved_pokemon": to,
                },
            )
        )

    def _reset_to_main_menu(self, dt):
        self.ui.switch_mode("main")
        self.ui.message_box.target_text = f"What will {self.your_battle.name} do?"
        self.ui.message_box.current_text = ""
        self.ui.message_box.dialog_text.text = ""

    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        self.ui.draw()
        self.enemy_sprite.draw()
        self.your_sprite.draw()
        self.ui.draw_hp_bar(self.your_battle.get_hp_ratio(), "player")
        self.ui.draw_exp_bar(self.your_battle.get_exp_ratio())
        self.ui.draw_hp_bar(self.enemy_battle.get_hp_ratio(), "enemy")

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
                    global_bus.publish(
                        OverlayViewEvent(
                            target="bag",
                            payload={
                                "previous_view": self,
                                "battle_system": self.battle_system,
                                "save_manager": self.player_manager,
                                "data_loader": self.data_loader,
                            },
                        )
                    )
                elif self.ui.menu_panel.selection_index == 2:
                    # Ask the Director to overlay the Pokémon menu
                    global_bus.publish(
                        OverlayViewEvent(
                            target="pokemon_menu",
                            payload={
                                "previous_view": self,
                                "save_manager": self.player_manager,
                                "data_loader": self.data_loader,
                                "battle_system": self.battle_system,
                            },
                        )
                    )
                elif self.ui.menu_panel.selection_index == 3:
                    if not self.is_trainer:
                        self.run()
                    else:
                        self.ui.queue_messages(["You cant run away from trainers!"])
                        self.ui.switch_mode("dialog")
                        arcade.schedule_once(self._reset_to_main_menu, 2)

            elif self.ui.active_component == "moves":
                self.start_turn(self.ui.menu_panel.selection_index)

        elif self.is_pressed(CONFIG.controls.cancel, symbol):
            if self.ui.active_component == "moves":
                self.ui.switch_mode("main")

    def is_pressed(self, config_key, symbol) -> bool:
        return getattr(arcade.key, config_key, None) == symbol

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
                    global_bus.publish(
                        OverlayViewEvent(
                            target="dialog",
                            payload={
                                "npc_id": self.npc_id,
                                "state": "after_victory",
                                "action": "end",
                            },
                        )
                    )
                    return

        # Tell the Director we are done — it will return to the Overworld
        global_bus.publish(CloseViewEvent())
