import arcade
from src.entities.pokemonSprites import Pokemon
from src.core.gameContext import saveManager, dataLoader
from data.config import Config
from src.states.evolvingView import EvolvingView
from src.ui.battleUi import BattleUi
from src.core.battleSystem import BattleSystem

CONFIG = Config.load()


class BattleView(arcade.View):
    def __init__(self, pokemon_name, pokemon_data, level, overworld_view):
        super().__init__()

        self.ui = BattleUi(self.whatHappendAfterText)

        self.overworld_view = overworld_view

        self.playerPokemon = saveManager.player.pokemon

        self.yourPokemon = Pokemon(
            self.playerPokemon[0].name,
            dataLoader.getPokemon(self.playerPokemon[0].name),
            self.playerPokemon[0].moves,
            level=self.playerPokemon[0].level,
            isEnemy=False,
            currentHp=self.playerPokemon[0].hp,
            exp=self.playerPokemon[0].exp,
        )
        self.enemyPokemon = Pokemon(
            pokemon_name,
            pokemon_data,
            [{"name": "tackle", "pp": 15}],
            level=level,
            isEnemy=True,
        )

        self.battleSystem = BattleSystem(
            self.yourPokemon.pokemonBattle, self.enemyPokemon.pokemonBattle
        )

        self.ui.setPlayerInformation(
            self.yourPokemon.pokemonBattle.name.upper(),
            self.yourPokemon.pokemonBattle.level,
        )
        self.ui.setEnemyInformation(
            self.enemyPokemon.pokemonBattle.name.upper(),
            self.enemyPokemon.pokemonBattle.level,
        )
        self.ui.switchMenu("main")
        self.updateUiMoves()
        first_move = dataLoader.getMove(self.yourPokemon.pokemonBattle.moves[0].name)

        self.ui.setMoveInformation(
            first_move.type, first_move.pp, self.yourPokemon.pokemonBattle.moves[0].pp
        )

        self.ui.setTransition(self.yourPokemon, self.enemyPokemon)

    def updateUiMoves(self):
        moves = self.yourPokemon.pokemonBattle.moves

        for i, button in enumerate(self.ui.moveButtons):
            if i < len(moves):
                button.text = moves[i].name.upper()
                button.visible = True
                button.enabled = True
            else:
                button.text = ""
                button.visible = False
                button.enabled = False

    def startTurn(self, index):
        self.ui.messageQueue.extend(self.battleSystem.turn(index))
        self.ui.switchMenu("dialog")
        self.ui.nextMessage()

    def whatHappendAfterText(self):
        if self.battleSystem.battleState == "currently turn":
            self.ui.messageQueue.extend(self.battleSystem.executeNextAction())
            self.ui.nextMessage()
        elif self.battleSystem.battleState in ["intro", "post turn"]:
            self.battleSystem.battleState = "waiting"
            arcade.schedule_once(self.resetToMainMenu, 0.5)
        elif self.battleSystem.battleState == "end":
            if self.battleSystem.exp > 0:
                result = self.yourPokemon.pokemonBattle.gainExp(self.battleSystem.exp)
                self.battleSystem.exp = 0

                if not result["isLeveledUp"] and not result["evolve"]["hasEvolved"]:
                    self.run()

                if result["isLeveledUp"]:
                    self.ui.player_lvl_label = (
                        f"Lv{self.yourPokemon.pokemonBattle.level}"
                    )
                    self.ui.manager.trigger_render()
                    self.ui.messageQueue.extend(
                        [
                            f"{self.yourPokemon.pokemonBattle.name} has leveled up!!!",
                            f"Now {self.yourPokemon.pokemonBattle.name} is {self.yourPokemon.pokemonBattle.level} lvl!!!",
                        ]
                    )
                    self.ui.isProcessingText = True

                if result["evolve"]["hasEvolved"]:
                    self.battleSystem.hasEvolved = True
                    self.battleSystem.save()
                    self.window.show_view(
                        EvolvingView(
                            self.overworld_view,
                            self.yourPokemon.pokemonBattle.name.lower(),
                            result["evolve"]["to"],
                        )
                    )
            else:
                self.run()

    def resetToMainMenu(self, dt):
        self.ui.switchMenu("main")
        self.ui.targetText = f"What will {self.yourPokemon.pokemonBattle.name} do?"
        self.ui.currentText = ""

    def on_draw(self):
        self.clear()

        self.window.default_camera.use()

        self.ui.draw()

        self.enemyPokemon.draw()
        self.yourPokemon.draw()

        self.ui.drawHpBar(self.yourPokemon.pokemonBattle.getHpRatio(), "player")
        self.ui.drawExpBar(self.yourPokemon.pokemonBattle.getExpRatio())
        self.ui.drawHpBar(self.enemyPokemon.pokemonBattle.getHpRatio(), "enemy")

    def on_update(self, delta_time):
        self.ui.update(delta_time)

    def on_key_press(self, key, modifiers):
        if self.ui.activeMenu == "main":
            current_list = self.ui.mainButtons
            num_buttons = len(current_list)
        else:
            current_list = self.ui.moveButtons
            num_buttons = len(self.yourPokemon.pokemonBattle.moves)

        if self.isPressed(CONFIG.controls.up, key):
            if num_buttons > 2:
                self.ui.selectionIndex = (self.ui.selectionIndex - 2) % num_buttons

            if self.ui.activeMenu == "moves":
                self.moveHover(self.ui.selectionIndex)
        elif self.isPressed(CONFIG.controls.down, key):
            if num_buttons > 2:
                self.ui.selectionIndex = (self.ui.selectionIndex + 2) % num_buttons

            if self.ui.activeMenu == "moves":
                self.moveHover(self.ui.selectionIndex)
        elif self.isPressed(CONFIG.controls.left, key):
            self.ui.selectionIndex = (self.ui.selectionIndex - 1) % num_buttons

            if self.ui.activeMenu == "moves":
                self.moveHover(self.ui.selectionIndex)
        elif self.isPressed(CONFIG.controls.right, key):
            self.ui.selectionIndex = (self.ui.selectionIndex + 1) % num_buttons

            if self.ui.activeMenu == "moves":
                self.moveHover(self.ui.selectionIndex)
        elif self.isPressed(CONFIG.controls.interact, key):
            if self.ui.activeMenu == "main":
                if self.ui.selectionIndex == 0:
                    self.ui.switchMenu("moves")
                elif self.ui.selectionIndex == 3:
                    self.run()
            elif self.ui.activeMenu == "moves":
                self.startTurn(self.ui.selectionIndex)
        elif self.isPressed(CONFIG.controls.cancel, key):
            if self.ui.activeMenu == "moves":
                self.ui.switchMenu("main")

    def isPressed(self, configKey, key) -> bool:
        return getattr(arcade.key, configKey, None) == key

    def moveHover(self, index):
        if index is not None:
            move_name = self.yourPokemon.pokemonBattle.moves[index].name

            move = dataLoader.getMove(move_name)
            self.ui.setMoveInformation(
                move.type, move.pp, self.yourPokemon.pokemonBattle.moves[index].pp
            )

    def run(self):
        self.window.show_view(self.overworld_view)
        self.battleSystem.save()
