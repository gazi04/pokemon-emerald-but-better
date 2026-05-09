import arcade
from src.entities.pokemonSprites import Pokemon
from src.core.gameContext import saveManager, dataLoader
import random
from data.config import Config
from src.states.evolvingView import EvolvingView
from src.ui.battleUi import BattleUi

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

        self.ui.setPlayerInformation(self.yourPokemon.pokemonBattle.name.upper(), self.yourPokemon.pokemonBattle.level)
        self.ui.setEnemyInformation(self.enemyPokemon.pokemonBattle.name.upper(), self.enemyPokemon.pokemonBattle.level)
        self.ui.switchMenu("main")
        self.updateUiMoves()
        first_move = dataLoader.getAMove(
            self.yourPokemon.pokemonBattle.moves[0].name)

        self.ui.setMoveInformation(first_move.type, first_move.pp, self.yourPokemon.pokemonBattle.moves[0].pp)

        self.turn_queue = []
        self.battleState = "intro"
        self.exp = 0
        self.hasEvolved = False
        
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

    def turn(self, moveIndex):
        self.battleState = "currently turn"
        self.ui.switchMenu("dialog")

        enemyMoveIndex = random.randint(
            0, len(self.enemyPokemon.pokemonBattle.moves) - 1)

        if self.yourPokemon.pokemonBattle.getStat("speed") >= self.enemyPokemon.pokemonBattle.getStat("speed"):
            self.turn_queue = [("player", moveIndex),
                               ("enemy", enemyMoveIndex)]
        else:
            self.turn_queue = [("enemy", enemyMoveIndex),
                               ("player", moveIndex)]

        self.execute_next_action()

    def execute_next_action(self):
        if not self.turn_queue:
            self.postTurn()
            return

        attacker_key, move_idx = self.turn_queue.pop(0)

        if attacker_key == "player" and self.yourPokemon.pokemonBattle.current_hp > 0:
            move_name = self.yourPokemon.pokemonBattle.moves[move_idx].name
            self.ui.messageQueue.append(
                f"{self.yourPokemon.pokemonBattle.name} used {move_name}!")
            result = self.yourPokemon.pokemonBattle.useMove(
                move_idx, self.enemyPokemon.pokemonBattle)
            self.ui.messageQueue.extend(result)
        elif attacker_key == "enemy" and self.enemyPokemon.pokemonBattle.current_hp > 0:
            move_name = self.enemyPokemon.pokemonBattle.moves[move_idx].name
            self.ui.messageQueue.append(
                f"Foe {self.enemyPokemon.pokemonBattle.name} used {move_name}!")
            result = self.enemyPokemon.pokemonBattle.useMove(
                move_idx, self.yourPokemon.pokemonBattle)
            self.ui.messageQueue.extend(result)

        self.ui.nextMessage()

    def whatHappendAfterText(self):
        if self.battleState == "currently turn":
            self.execute_next_action()
        elif self.battleState in ["intro", "post turn"]:
            self.battleState = "waiting"
            arcade.schedule_once(self.resetToMainMenu, 0.5)
        elif self.battleState == "end":
            if self.exp > 0:
                result = self.yourPokemon.pokemonBattle.gainExp(self.exp)
                self.exp = 0

                if not result["isLeveledUp"] and not result["evolve"]["hasEvolved"]:
                    self.run()

                if result["isLeveledUp"]:
                    self.player_lvl_label = f"Lv{self.yourPokemon.pokemonBattle.level}"
                    self.manager.trigger_render()
                    self.ui.messageQueue.extend(
                        [
                            f"{self.yourPokemon.pokemonBattle.name} has leveled up!!!",
                            f"Now {self.yourPokemon.pokemonBattle.name} is {self.yourPokemon.pokemonBattle.level} lvl!!!",
                        ]
                    )
                    self.isProcessingText = True

                if result["evolve"]["hasEvolved"]:
                    self.hasEvolved = True
                    self.save()
                    self.window.show_view(
                        EvolvingView(
                            self.overworld_view,
                            self.yourPokemon.pokemonBattle.name.lower(),
                            result["evolve"]["to"],
                        )
                    )
            else:
                self.run()

    def pokemonDeath(self, diedPokemon: Pokemon):
        self.battleState = "end"
        if diedPokemon.isEnemy:
            self.exp = diedPokemon.getExp()

            self.ui.messageQueue.extend(
                [
                    f"Wild {self.enemyPokemon.pokemonBattle.name} fainted!",
                    f"{self.yourPokemon.pokemonBattle.name} gained {self.exp} EXP. Points!",
                ]
            )

            self.ui.nextMessage()
            self.ui.switchMenu("dialog")
        else:
            self.ui.messageQueue.extend(
                [f"{self.yourPokemon.pokemonBattle.name} fainted!"])

            self.nextMessage()
            self.switchMenu("dialog")

    def postTurn(self):
        list = []

        list.extend(self.yourPokemon.pokemonBattle.afterATurn())
        list.extend(self.enemyPokemon.pokemonBattle.afterATurn())

        if self.yourPokemon.pokemonBattle.current_hp <= 0:
            self.pokemonDeath(self.yourPokemon.pokemonBattle)
            return

        if self.enemyPokemon.pokemonBattle.current_hp <= 0:
            self.pokemonDeath(self.enemyPokemon.pokemonBattle)
            return

        if len(list) - 1 > 0:
            self.battleState = "post turn"

            self.ui.messageQueue.extend(list)

            self.ui.nextMessage()
            self.ui.switchMenu("dialog")
        else:
            self.battleState = "waiting"
            arcade.schedule_once(self.resetToMainMenu, 0.5)

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

        if self.is_pressed(CONFIG.controls.up, key):
            if num_buttons > 2:
                self.ui.selectionIndex = (self.ui.selectionIndex - 2) % num_buttons

            if self.ui.activeMenu == "moves":
                self.moveHover(self.ui.selectionIndex)
        elif self.is_pressed(CONFIG.controls.down, key):
            if num_buttons > 2:
                self.ui.selectionIndex = (self.ui.selectionIndex + 2) % num_buttons

            if self.ui.activeMenu == "moves":
                self.moveHover(self.ui.selectionIndex)
        elif self.is_pressed(CONFIG.controls.left, key):
            self.ui.selectionIndex = (self.ui.selectionIndex - 1) % num_buttons

            if self.ui.activeMenu == "moves":
                self.moveHover(self.ui.selectionIndex)
        elif self.is_pressed(CONFIG.controls.right, key):
            self.ui.selectionIndex = (self.ui.selectionIndex + 1) % num_buttons

            if self.ui.activeMenu == "moves":
                self.moveHover(self.ui.selectionIndex)

        elif self.is_pressed(CONFIG.controls.interact, key):
            if self.ui.activeMenu == "main":
                if self.ui.selectionIndex == 0:
                    self.ui.switchMenu("moves")
                elif self.ui.selectionIndex == 3:
                    self.run()
            elif self.ui.activeMenu == "moves":
                self.turn(self.ui.selectionIndex)
        elif self.is_pressed(CONFIG.controls.cancel, key):
            if self.ui.activeMenu == "moves":
                self.ui.switchMenu("main")

    def is_pressed(self, configKey, key):
        return getattr(arcade.key, configKey, None) == key

    def moveHover(self, index):
        if index is not None:
            move_name = self.yourPokemon.pokemonBattle.moves[index].name

            move = dataLoader.getAMove(move_name)
            self.ui.setMoveInformation(move.type, move.pp, self.yourPokemon.pokemonBattle.moves[index].pp)

    def run(self):
        self.window.show_view(self.overworld_view)
        self.save()

    def save(self):
        pass
        # saveManager.updateHp(self.your_pokemon.pokemonBattle.pokemonBattle.name, self.your_pokemon.pokemonBattle.current_hp)
        # for move in self.your_pokemon.pokemonBattle.pokemonBattle.moves:
        #     saveManager.updateMove(self.your_pokemon.pokemonBattle.pokemonBattle.name, self.move[""])

        # if not self.hasEvolved:
        #     saveManager.updateLevel(
        #         self.your_pokemon.pokemonBattle.name, self.your_pokemon.pokemonBattle.level, self.your_pokemon.pokemonBattle.exp
        #     )
        # else:
        #     saveManager.updateLevel(
        #         self.your_pokemon.pokemonBattle.name,
        #         self.your_pokemon.pokemonBattle.level,
        #         self.your_pokemon.pokemonBattle.exp,
        #         self.your_pokemon.pokemonBattle.evolution["to"],
        #     )
