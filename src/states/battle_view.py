import arcade
from src.core.data_loader import DataLoader
from src.core.save_manager import SaveManager
from src.model.player import PlayerPokemon, PlayerPokemonMove
from src.model.trainer import Trainer
from src.entities.pokemon_sprites import Pokemon
from src.entities.pokemon_battle import PokemonBattle
from data.config import Config
from src.ui.battle_ui_manager import BattleUiManager
from src.systems.battle_system import BattleSystem
from src.core.event_bus import global_bus
from src.core.events import CloseViewEvent, OverlayViewEvent, SwapViewEvent

CONFIG = Config.load()


class BattleView(arcade.View):
    def __init__(
        self,
        overworld_view,
        save_manager: SaveManager,
        data_loader: DataLoader,
        foe_pokemon_name=None,
        foe_pokemon_data=None,
        foe_level=None,
        is_trainer=False,
        trainer_data: Trainer = None
    ):
        super().__init__()

        self.overworld_view = overworld_view
        self.save_manager = save_manager
        self.data_loader = data_loader

        self.ui = BattleUiManager(self.whatHappendAfterText)

        self.playerPokemon = self.save_manager.player.pokemon

        player_profile = data_loader.get_pokemon(self.playerPokemon[0].name)
        if player_profile is None:
            raise ValueError(
                f"Player pokemon data for '{self.playerPokemon[0].name}' could not be loaded."
            )

        self.yourPokemon = Pokemon(
            player_profile,
            False,
            self.playerPokemon[0],
        )

        self.is_trainer = is_trainer

        if not is_trainer:
            if foe_pokemon_data is None:
                raise ValueError(
                    f"Enemy pokemon data for '{foe_pokemon_name}' cannot be None.")

            self.enemyPokemon = Pokemon(
                foe_pokemon_data,
                True,
                name=foe_pokemon_name,
                moves=[PlayerPokemonMove("tackle", 35)],
                level=foe_level,
            )
        else:
            first = trainer_data.party[0]
            first_profile = data_loader.get_pokemon(first.name)
            if first_profile is None:
                raise ValueError(
                    f"Trainer pokemon '{first.name}' not found in data.")

            self.enemyPokemon = Pokemon(
                first_profile,
                True,
                name=first.name,
                moves=first.moves,
                level=first.level,
            )
            trainer_data.party.pop(0)

        self.save_manager.player.mark_seen(foe_pokemon_name)

        self.battleSystem = BattleSystem(
            self.yourPokemon.pokemonBattle,
            self.enemyPokemon.pokemonBattle,
            self.save_manager,
            self.data_loader,
            is_trainer,
            trainer_data,
        )

        self.ui.set_player_info(
            self.yourPokemon.pokemonBattle.name.upper(),
            self.yourPokemon.pokemonBattle.level,
        )
        self.ui.set_enemy_info(
            self.enemyPokemon.pokemonBattle.name.upper(),
            self.enemyPokemon.pokemonBattle.level,
        )
        self.ui.switch_mode("main")
        self.updateUiMoves()

        first_move = data_loader.get_move(
            self.yourPokemon.pokemonBattle.moves[0].name)
        if first_move is not None:
            self.ui.menu_panel.update_move_info(
                first_move.type,
                self.yourPokemon.pokemonBattle.moves[0].pp,
                first_move.pp,
            )
        else:
            self.ui.menu_panel.update_move_info(
                "Normal", self.yourPokemon.pokemonBattle.moves[0].pp, 35
            )

        self.ui.set_transition(self.yourPokemon, self.enemyPokemon, is_trainer)

    def updateUiMoves(self):
        moves = self.yourPokemon.pokemonBattle.moves
        for i, button in enumerate(self.ui.menu_panel.move_buttons):
            if i < len(moves):
                button.text = moves[i].name.upper()
                button.visible = True
                button.enabled = True
            else:
                button.text = ""
                button.visible = False
                button.enabled = False

    def startTurn(self, index):
        self.ui.queue_messages(self.battleSystem.turn(index))
        self.ui.switch_mode("dialog")

    def onItemUsed(self, itemIndex: int):
        self.ui.queue_messages(self.battleSystem.turnUseItem(itemIndex))
        self.ui.switch_mode("dialog")
        
    def switch_turn(self):
        self.battleSystem.battleState = "switching"
        
        self.ui.switch_mode("dialog")
        self.ui.queue_messages(self.battleSystem.switch_pokemon())
        
        self.ui.set_player_info(
            self.yourPokemon.pokemonBattle.name.upper(),
            self.yourPokemon.pokemonBattle.level,
        )
        self.updateUiMoves()
        
        texture = self.data_loader.get_pokemon(self.yourPokemon.pokemonBattle.name.lower()).sprites.back
        self.yourPokemon.setNewTexture(texture)
        
    def whatHappendAfterText(self):
        if self.battleSystem.battleState == "caught":
            enemy = self.battleSystem.enemyPokemon
            self.save_manager.player.add_pokemon(PlayerPokemon(
                name=enemy.name.lower(),
                hp=enemy.currentHp,
                level=enemy.level,
                exp=0,
                moves=enemy.moves,
            ))
            self.run()
            return

        if self.battleSystem.battleState == "currently turn":
            self._on_continue_turn()
        elif self.battleSystem.battleState in ["intro", "post turn", "waiting"]:
            self._ending_turn()
            
        elif self.battleSystem.battleState == "switching":
            self.ui.queue_messages(self.battleSystem.switch_turn())
            self.ui.switch_mode("dialog")
        
        elif self.battleSystem.battleState == "trainer switch":
            self._trainer_give_exp()
        elif self.battleSystem.battleState == "trainer sending":
            self._trainer_send_next_pokemon()
        elif self.battleSystem.battleState == "end":
            self._handle_battle_finishing()

    def _on_continue_turn(self):
        messages = self.battleSystem.executeNextAction()
        if messages:
            self.ui.queue_messages(messages)
        else:
            self._ending_turn()

    def _ending_turn(self):
        self.battleSystem.battleState = "waiting"
        arcade.schedule_once(self._reset_to_main_menu, 0.5)

    def _trainer_give_exp(self):
        result = self.yourPokemon.pokemonBattle.gainExp(self.battleSystem.exp)
        self.battleSystem.exp = 0
        self.battleSystem.battleState = "trainer sending"

        if result["isLeveledUp"]:
            self._on_level_up(self.yourPokemon.pokemonBattle)
        else:
            self._trainer_send_next_pokemon()

    def _trainer_send_next_pokemon(self):
        next_data = self.battleSystem.next_trainer_pokemon

        if not next_data:
            self.ui.queue_messages(["Trainer was defeated!!!"])
            self.battleSystem.battleState = "end"
            return

        profile = self.data_loader.get_pokemon(next_data.name)

        texture = profile.sprites.front
        self.enemyPokemon.texture = arcade.load_texture(texture)
        self.enemyPokemon.pokemonBattle = PokemonBattle(
            profile,
            True,
            name=next_data.name,
            moves=next_data.moves,
            level=next_data.level,
        )
        self.battleSystem.enemyPokemon = self.enemyPokemon.pokemonBattle

        self.ui.set_enemy_info(next_data.name.upper(), next_data.level)
        self.ui.queue_messages([f"Trainer sent out {next_data.name}!"])
        self.battleSystem.battleState = "waiting"

    def _handle_battle_finishing(self):
        if self.battleSystem.exp <= 0:
            self.run()
            return

        result = self.yourPokemon.pokemonBattle.gainExp(self.battleSystem.exp)
        self.battleSystem.exp = 0

        if result["evolve"]["hasEvolved"]:
            self._evolution(self.yourPokemon.pokemonBattle.name.lower(), result["evolve"]["to"])
        elif result["isLeveledUp"]:
            self._on_level_up(self.yourPokemon.pokemonBattle)
        else:
            self.run()

    def _on_level_up(self, pokemon: PokemonBattle):
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
        self.battleSystem.hasEvolved = True
        self.battleSystem.save()
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
        self.ui.message_box.target_text = (
            f"What will {self.yourPokemon.pokemonBattle.name} do?"
        )
        self.ui.message_box.current_text = ""
        self.ui.message_box.dialog_text.text = ""

    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        self.ui.draw()
        self.enemyPokemon.draw()
        self.yourPokemon.draw()
        self.ui.draw_hp_bar(
            self.yourPokemon.pokemonBattle.getHpRatio(), "player")
        self.ui.draw_exp_bar(self.yourPokemon.pokemonBattle.getExpRatio())
        self.ui.draw_hp_bar(
            self.enemyPokemon.pokemonBattle.getHpRatio(), "enemy")

    def on_update(self, delta_time):
        self.ui.update(delta_time)

    def on_key_press(self, symbol: int, modifiers: int):
        if self.ui.active_component == "main":
            current_list = self.ui.menu_panel.main_buttons
            num_buttons = len(current_list)
        elif self.ui.active_component == "moves":
            current_list = self.ui.menu_panel.move_buttons
            num_buttons = len(self.yourPokemon.pokemonBattle.moves)
        else:
            return

        if self.isPressed(CONFIG.controls.up, symbol):
            if num_buttons > 2:
                self.ui.menu_panel.selection_index = (
                    self.ui.menu_panel.selection_index - 2
                ) % num_buttons
            if self.ui.active_component == "moves":
                self.moveHover(self.ui.menu_panel.selection_index)

        elif self.isPressed(CONFIG.controls.down, symbol):
            if num_buttons > 2:
                self.ui.menu_panel.selection_index = (
                    self.ui.menu_panel.selection_index + 2
                ) % num_buttons
            if self.ui.active_component == "moves":
                self.moveHover(self.ui.menu_panel.selection_index)

        elif self.isPressed(CONFIG.controls.left, symbol):
            self.ui.menu_panel.selection_index = (
                self.ui.menu_panel.selection_index - 1
            ) % num_buttons
            if self.ui.active_component == "moves":
                self.moveHover(self.ui.menu_panel.selection_index)

        elif self.isPressed(CONFIG.controls.right, symbol):
            self.ui.menu_panel.selection_index = (
                self.ui.menu_panel.selection_index + 1
            ) % num_buttons
            if self.ui.active_component == "moves":
                self.moveHover(self.ui.menu_panel.selection_index)

        elif self.isPressed(CONFIG.controls.interact, symbol):
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
                                "battle_system": self.battleSystem,
                                "save_manager": self.save_manager,
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
                                "save_manager": self.save_manager,
                                "data_loader": self.data_loader,
                                "battle_system": self.battleSystem
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
                self.startTurn(self.ui.menu_panel.selection_index)

        elif self.isPressed(CONFIG.controls.cancel, symbol):
            if self.ui.active_component == "moves":
                self.ui.switch_mode("main")

    def isPressed(self, configKey, symbol) -> bool:
        return getattr(arcade.key, configKey, None) == symbol

    def moveHover(self, index):
        if index is not None and index < len(self.yourPokemon.pokemonBattle.moves):
            move_name = self.yourPokemon.pokemonBattle.moves[index].name
            move = self.data_loader.get_move(move_name)

            # FIX 6 & 7: Wrapped with an if statement to verify 'move' is found before grabbing properties
            if move is not None:
                self.ui.menu_panel.update_move_info(
                    move.type,
                    self.yourPokemon.pokemonBattle.moves[index].pp,
                    move.pp,
                )

    def run(self):
        self.battleSystem.save()
        global_bus.publish(CloseViewEvent())
