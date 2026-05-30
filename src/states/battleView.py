import arcade
from src.model.player import PlayerPokemonMove
from src.entities.pokemonSprites import Pokemon
from src.core.gameContext import saveManager, dataLoader
from data.config import Config
from src.states.evolvingView import EvolvingView
from src.states.bagView import BagView
from src.states.pokemonMenuView import PokemonMenuView
from src.ui.battle_ui_manager import BattleUiManager
from src.core.battleSystem import BattleSystem
from src.core.event_bus import global_bus
from src.core.events import CloseViewEvent, OverlayViewEvent, SwapViewEvent

CONFIG = Config.load()


class BattleView(arcade.View):
    def __init__(self, pokemon_name, pokemon_data, level, overworld_view):
        super().__init__()

        # overworld_view is kept only so the flicker transition in OverworldView
        # still works. The Director owns the actual navigation.
        self.overworld_view = overworld_view

        self.ui = BattleUiManager(self.whatHappendAfterText)

        self.playerPokemon = saveManager.player.pokemon

        self.yourPokemon = Pokemon(
            dataLoader.getPokemon(self.playerPokemon[0].name),
            False,
            self.playerPokemon[0],
        )
        self.enemyPokemon = Pokemon(
            pokemon_data,
            True,
            name=pokemon_name,
            moves=[PlayerPokemonMove("tackle", 35)],
            level=level,
        )

        self.battleSystem = BattleSystem(
            self.yourPokemon.pokemonBattle, self.enemyPokemon.pokemonBattle
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

        first_move = dataLoader.getMove(self.yourPokemon.pokemonBattle.moves[0].name)
        self.ui.menu_panel.update_move_info(
            first_move.type,
            self.yourPokemon.pokemonBattle.moves[0].pp,
            first_move.pp,
        )

        self.ui.set_transition(self.yourPokemon, self.enemyPokemon)

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

    def whatHappendAfterText(self):
        if self.battleSystem.battleState == "currently turn":
            messages = self.battleSystem.executeNextAction()
            if messages:
                self.ui.queue_messages(messages)
            else:
                self.battleSystem.battleState = "waiting"
                arcade.schedule_once(self.resetToMainMenu, 0.5)

        elif self.battleSystem.battleState in ["intro", "post turn", "waiting"]:
            self.battleSystem.battleState = "waiting"
            arcade.schedule_once(self.resetToMainMenu, 0.5)

        elif self.battleSystem.battleState == "end":
            if self.battleSystem.exp > 0:
                result = self.yourPokemon.pokemonBattle.gainExp(self.battleSystem.exp)
                self.battleSystem.exp = 0

                if not result["isLeveledUp"] and not result["evolve"]["hasEvolved"]:
                    self.run()
                    return

                if result["isLeveledUp"]:
                    self.ui.set_player_info(
                        self.yourPokemon.pokemonBattle.name.upper(),
                        self.yourPokemon.pokemonBattle.level,
                    )
                    self.ui.manager.trigger_render()
                    self.ui.queue_messages(
                        [
                            f"{self.yourPokemon.pokemonBattle.name} has leveled up!!!",
                            f"Now {self.yourPokemon.pokemonBattle.name} is {self.yourPokemon.pokemonBattle.level} lvl!!!",
                        ]
                    )

                if result["evolve"]["hasEvolved"]:
                    self.battleSystem.hasEvolved = True
                    self.battleSystem.save()
                    # Ask the Director to swap to the Evolution view
                    global_bus.publish(
                        SwapViewEvent(
                            target="evolving",
                            payload={
                                "pokemon": self.yourPokemon.pokemonBattle.name.lower(),
                                "evolved_pokemon": result["evolve"]["to"],
                            },
                        )
                    )
            else:
                self.run()

    def resetToMainMenu(self, dt):
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
        self.ui.draw_hp_bar(self.yourPokemon.pokemonBattle.getHpRatio(), "player")
        self.ui.draw_exp_bar(self.yourPokemon.pokemonBattle.getExpRatio())
        self.ui.draw_hp_bar(self.enemyPokemon.pokemonBattle.getHpRatio(), "enemy")

    def on_update(self, delta_time):
        self.ui.update(delta_time)

    def on_key_press(self, key, modifiers):
        if self.ui.active_component == "main":
            current_list = self.ui.menu_panel.main_buttons
            num_buttons = len(current_list)
        elif self.ui.active_component == "moves":
            current_list = self.ui.menu_panel.move_buttons
            num_buttons = len(self.yourPokemon.pokemonBattle.moves)
        else:
            return

        if self.isPressed(CONFIG.controls.up, key):
            if num_buttons > 2:
                self.ui.menu_panel.selection_index = (
                    self.ui.menu_panel.selection_index - 2
                ) % num_buttons
            if self.ui.active_component == "moves":
                self.moveHover(self.ui.menu_panel.selection_index)

        elif self.isPressed(CONFIG.controls.down, key):
            if num_buttons > 2:
                self.ui.menu_panel.selection_index = (
                    self.ui.menu_panel.selection_index + 2
                ) % num_buttons
            if self.ui.active_component == "moves":
                self.moveHover(self.ui.menu_panel.selection_index)

        elif self.isPressed(CONFIG.controls.left, key):
            self.ui.menu_panel.selection_index = (
                self.ui.menu_panel.selection_index - 1
            ) % num_buttons
            if self.ui.active_component == "moves":
                self.moveHover(self.ui.menu_panel.selection_index)

        elif self.isPressed(CONFIG.controls.right, key):
            self.ui.menu_panel.selection_index = (
                self.ui.menu_panel.selection_index + 1
            ) % num_buttons
            if self.ui.active_component == "moves":
                self.moveHover(self.ui.menu_panel.selection_index)

        elif self.isPressed(CONFIG.controls.interact, key):
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
                            },
                        )
                    )
                elif self.ui.menu_panel.selection_index == 2:
                    # Ask the Director to overlay the Pokémon menu
                    global_bus.publish(
                        OverlayViewEvent(
                            target="pokemon_menu",
                            payload={"previous_view": self},
                        )
                    )
                elif self.ui.menu_panel.selection_index == 3:
                    self.run()
            elif self.ui.active_component == "moves":
                self.startTurn(self.ui.menu_panel.selection_index)

        elif self.isPressed(CONFIG.controls.cancel, key):
            if self.ui.active_component == "moves":
                self.ui.switch_mode("main")

    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key

    def moveHover(self, index):
        if index is not None and index < len(self.yourPokemon.pokemonBattle.moves):
            move_name = self.yourPokemon.pokemonBattle.moves[index].name
            move = dataLoader.getMove(move_name)
            self.ui.menu_panel.update_move_info(
                move.type,
                self.yourPokemon.pokemonBattle.moves[index].pp,
                move.pp,
            )

    def run(self):
        self.battleSystem.save()
        # Tell the Director we are done — it will return to the Overworld
        global_bus.publish(CloseViewEvent())
