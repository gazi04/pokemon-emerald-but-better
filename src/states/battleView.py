import arcade
import arcade.gui
from src.entities.pokemon import Pokemon
from src.util import getAMove, getPlayersPokemon, updateHp, updateMove, updateLevel
import random
from data.config import Config
from src.states.evolvingView import EvolvingView

CONFIG = Config.load()


class BattleView(arcade.View):
    def __init__(self, pokemon_name, pokemon_data, level, overworld_view):
        super().__init__()

        self.overworld_view = overworld_view

        self.tilemap = arcade.tilemap.load_tilemap(
            "assets/ui/battle/battleUiDesign.tmx"
        )

        self.playerPokemon = getPlayersPokemon()
        move_button_style = {
            "normal": arcade.gui.UIFlatButton.UIStyle(
                font_size=24,
                font_name="Pokemon Emerald",
                font_color=arcade.color.BLACK,
                bg=arcade.color.WHITE,
                border=arcade.color.WHITE,
                border_width=0,
            ),
            "hover": arcade.gui.UIFlatButton.UIStyle(
                font_size=24,
                font_name="Pokemon Emerald",
                font_color=arcade.color.GRAY,
                bg=arcade.color.WHITE,
                border=arcade.color.WHITE,
                border_width=0,
            ),
            "press": arcade.gui.UIFlatButton.UIStyle(
                font_size=22,
                font_name="Pokemon Emerald",
                font_color=arcade.color.WHITE,
                bg=arcade.color.WHITE,
                border=arcade.color.WHITE,
                border_width=0,
            ),
        }

        self.your_pokemon = Pokemon(
            self.playerPokemon[0]["name"],
            self.playerPokemon[0],
            self.playerPokemon[0]["moves"],
            level=self.playerPokemon[0]["level"],
            isEnemy=False,
            currentHp=self.playerPokemon[0]["hp"],
            exp=self.playerPokemon[0]["exp"],
        )
        self.enemy_pokemon = Pokemon(
            pokemon_name,
            pokemon_data,
            [{"name": "tackle", "pp": 15}],
            level=level,
            isEnemy=True,
        )

        self.manager = arcade.gui.UIManager()
        self.manager.enable()
        self.manager._pixelated = True

        self.main_menu_container = arcade.gui.UIWidget()
        self.move_menu_container = arcade.gui.UIWidget()
        self.dialog_menu_container = arcade.gui.UIWidget()

        self.targetText = ""
        self.currentText = ""
        self.textDelayTimer = 0
        self.messageQueue = []
        self.isProcessingText = False

        self.hp_bars = {}
        self.bagBtn = None
        self.fightBtn = None
        self.pokemonBtn = None
        self.runBtn = None

        raw_map_height = (
            self.tilemap.tiled_map.map_size.height
            * self.tilemap.tiled_map.tile_size.height
        )

        for layer in self.tilemap.tiled_map.layers:
            layer_name = layer.name

            current_layer = self.tilemap.get_tilemap_layer(layer_name)

            for obj in current_layer.tiled_objects:
                w = int(obj.size.width / 32)
                h = int(obj.size.height / 32)

                x = int(obj.coordinates.x / 32)
                y = int((raw_map_height - obj.coordinates.y) / 32)

                # --- UI TEXTURES (Buttons/Frames) ---
                if obj.name == "background":
                    sprite = arcade.load_texture("assets/ui/battle/background.png")

                    self.background = arcade.gui.UIImage(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        texture=sprite,
                    )
                    self.manager.add(self.background)
                elif obj.name == "playerPlatform":
                    sprite = arcade.load_texture("assets/ui/battle/battlePlatform.png")

                    self.playerPlatform = arcade.gui.UIImage(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        texture=sprite,
                    )
                    self.manager.add(self.playerPlatform)
                elif obj.name == "enemyPlatform":
                    sprite = arcade.load_texture("assets/ui/battle/battlePlatform.png")

                    self.enemyPlatform = arcade.gui.UIImage(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        texture=sprite,
                    )
                    self.manager.add(self.enemyPlatform)
                elif obj.name == "dialogBox":
                    sprite = arcade.load_texture("assets/ui/battle/dialogbox.png")
                    self.dialogBox = arcade.gui.UIImage(
                        x=x, y=y, width=w, height=h, texture=sprite
                    )
                    self.main_menu_container.add(self.dialogBox)
                    self.dialog_menu_container.add(self.dialogBox)

                elif obj.name == "box":
                    sprite = arcade.load_texture("assets/ui/battle/box.png")
                    self.box = arcade.gui.UITextureButton(
                        x=x, y=y, width=w, height=h, texture=sprite
                    )
                    self.main_menu_container.add(self.box)

                elif obj.name == "fight":
                    sprite = arcade.load_texture("assets/ui/battle/fightButton.png")
                    self.fightBtn = arcade.gui.UITextureButton(
                        x=x, y=y, width=w, height=h, texture=sprite
                    )
                    self.fightBtn.on_click = lambda event: self.switchMenu("moves")

                    self.main_menu_container.add(self.fightBtn)

                elif obj.name == "run":
                    sprite = arcade.load_texture("assets/ui/battle/runButton.png")
                    self.runBtn = arcade.gui.UITextureButton(
                        x=x, y=y, width=w, height=h, texture=sprite
                    )
                    self.runBtn.on_click = lambda event: self.run()
                    self.main_menu_container.add(self.runBtn)

                elif obj.name == "pokemon":
                    sprite = arcade.load_texture("assets/ui/battle/pokemonButton.png")
                    self.pokemonBtn = arcade.gui.UITextureButton(
                        x=x, y=y, width=w, height=h, texture=sprite
                    )
                    self.main_menu_container.add(self.pokemonBtn)

                elif obj.name == "bag":
                    sprite = arcade.load_texture("assets/ui/battle/bagButton.png")
                    self.bagBtn = arcade.gui.UITextureButton(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite,
                    )
                    self.main_menu_container.add(self.bagBtn)

                if obj.name == "move1":
                    self.moveBtn1 = arcade.gui.UIFlatButton(
                        x=x,
                        y=y - h,
                        width=w,
                        height=h,
                        style=move_button_style,
                        bg=(255, 255, 255, 255),
                    )
                    self.move_menu_container.add(self.moveBtn1)

                if obj.name == "move2":
                    self.moveBtn2 = arcade.gui.UIFlatButton(
                        x=x,
                        y=y - h,
                        width=w,
                        height=h,
                        style=move_button_style,
                    )
                    self.move_menu_container.add(self.moveBtn2)

                if obj.name == "move3":
                    self.moveBtn3 = arcade.gui.UIFlatButton(
                        x=x,
                        y=y - h,
                        width=w,
                        height=h,
                        style=move_button_style,
                    )
                    self.move_menu_container.add(self.moveBtn3)

                if obj.name == "move4":
                    self.moveBtn4 = arcade.gui.UIFlatButton(
                        x=x,
                        y=y - h,
                        width=w,
                        height=h,
                        style=move_button_style,
                    )
                    self.move_menu_container.add(self.moveBtn4)

                elif obj.name == "movesBox":
                    sprite = arcade.load_texture("assets/ui/battle/movesBox.png")
                    self.move_menu_container.add(
                        arcade.gui.UIImage(
                            x=x,
                            y=y,
                            width=w,
                            height=h,
                            texture=sprite,
                            texture_hovered=sprite,
                            texture_pressed=sprite,
                        )
                    )

                elif obj.name == "player_hp_widget":
                    sprite = arcade.load_texture("assets/ui/battle/playerHpBar.png")
                    self.player_hp_widget = arcade.gui.UIImage(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite,
                    )
                    self.manager.add(self.player_hp_widget)

                elif obj.name == "enemy_hp_widget":
                    sprite = arcade.load_texture("assets/ui/battle/enemyHpBar.png")
                    self.enemy_hp_widget = arcade.gui.UIImage(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite,
                    )
                    self.manager.add(self.enemy_hp_widget)

                # --- UI LABELS (Names and Levels) ---
                elif obj.name == "player_name":
                    self.player_name_label = arcade.gui.UILabel(
                        text=self.your_pokemon.name.upper(),
                        x=x,
                        y=y - h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.manager.add(self.player_name_label)

                elif obj.name == "player_lvl":
                    self.player_lvl_label = arcade.gui.UILabel(
                        text=f"Lv{self.your_pokemon.level}",
                        x=x,
                        y=y - h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.manager.add(self.player_lvl_label)

                elif obj.name == "enemy_name":
                    self.enemy_name_label = arcade.gui.UILabel(
                        text=self.enemy_pokemon.name.upper(),
                        x=x,
                        y=y - h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.manager.add(self.enemy_name_label)

                elif obj.name == "enemy_lvl":
                    self.enemy_lvl_label = arcade.gui.UILabel(
                        text=f"Lv{self.enemy_pokemon.level}",
                        x=x,
                        y=y - h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.manager.add(self.enemy_lvl_label)

                elif obj.name == "maxPP":
                    self.maxPP = arcade.gui.UILabel(
                        x=x,
                        y=y - h,
                        width=w,
                        height=h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.move_menu_container.add(self.maxPP)

                elif obj.name == "currentPP":
                    self.currPP = arcade.gui.UILabel(
                        x=x,
                        y=y - h,
                        width=w,
                        height=h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.move_menu_container.add(self.currPP)

                elif obj.name == "type":
                    self.type = arcade.gui.UILabel(
                        x=x,
                        y=y - h,
                        width=w,
                        height=h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.move_menu_container.add(self.type)

                if obj.name == "dialog":
                    self.dialog = arcade.gui.UILabel(
                        x=x,
                        y=y - h,
                        width=w,
                        height=h,
                        text_color=arcade.color.WHITE,
                        font_name="Pokemon Emerald",
                        font_size=25,
                        align="left",
                    )
                    self.main_menu_container.add(self.dialog)
                    self.dialog_menu_container.add(self.dialog)

                # --- HP BAR FILL AREAS ---
                elif obj.name == "player_hp_fill":
                    self.hp_bars["player"] = {
                        "x": x,
                        "y": y - h,
                        "w": w,
                        "h": h,
                    }

                elif obj.name == "enemy_hp_fill":
                    self.hp_bars["enemy"] = {
                        "x": x,
                        "y": y - h,
                        "w": w,
                        "h": h,
                    }

                elif obj.name == "player_xp_fill":
                    self.expBar = {
                        "x": x,
                        "y": y - h,
                        "w": w,
                        "h": h,
                    }

        self.cursor_text = arcade.Text(
            "▶",
            0, 0, # Start at 0,0
            arcade.color.BLACK,
            font_size=24,
            anchor_y="center",
            font_name="Pokemon Emerald"
        )

        self.switchMenu("main")
        self.updateUiMoves()
        first_move = getAMove(self.your_pokemon.moves[0]["name"])

        self.type.text = first_move["type"]
        self.maxPP.text = first_move["pp"]
        self.currPP.text = self.your_pokemon.moves[0]["pp"]

        self.active_menu = "main"
        self.selection_index = 0

        self.main_buttons = [self.fightBtn, self.bagBtn, self.pokemonBtn, self.runBtn]
        self.move_buttons = [self.moveBtn1, self.moveBtn2, self.moveBtn3, self.moveBtn4]

        self.turn_queue = []
        self.battleState = "intro"
        self.exp = 0
        self.hasEvolved = False

        self.isSliding = True
        self.targetX = self.player_hp_widget.center_x
        self.transition()

    def transition(self):
        self.messageQueue = [
            f"A foe {self.enemy_pokemon.name} appeared!",
            f"Go! {self.your_pokemon.name}!",
        ]

        self.nextMessage()
        self.switchMenu("dialog")
        self.player_hp_widget.center_x += 400
        self.player_lvl_label.center_x += 400
        self.player_name_label.center_x += 400
        self.hp_bars["player"]["x"] += 400
        self.expBar["x"] += 400
        self.playerPlatform.center_x -= 400
        self.your_pokemon.center_x -= 400

        self.enemy_hp_widget.center_x -= 400
        self.enemy_lvl_label.center_x -= 400
        self.enemy_name_label.center_x -= 400
        self.hp_bars["enemy"]["x"] -= 400
        self.enemy_pokemon.center_x += 400
        self.enemyPlatform.center_x += 400

    def drawHpBar(self, pokemon, barData):
        if not barData:
            return

        ratio = pokemon.getHpRatio()
        fullWidth = barData["w"]
        currentWidth = fullWidth * ratio

        color = arcade.color.GREEN
        if ratio < 0.2:
            color = arcade.color.RED
        elif ratio < 0.5:
            color = arcade.color.GOLD

        arcade.draw_lrbt_rectangle_filled(
            left=barData["x"],
            right=barData["x"] + currentWidth,
            bottom=barData["y"],
            top=barData["y"] + barData["h"],
            color=color,
        )

    def drawExpBar(self):
        if not self.expBar:
            return

        ratio = self.your_pokemon.getExpRatio()
        fullWidth = self.expBar["w"]
        currentWidth = fullWidth * ratio

        arcade.draw_lrbt_rectangle_filled(
            left=self.expBar["x"],
            right=self.expBar["x"] + currentWidth,
            bottom=self.expBar["y"],
            top=self.expBar["y"] + self.expBar["h"],
            color=arcade.color.CYAN,
        )

    def switchMenu(self, menu_to_show):
        self.active_menu = menu_to_show
        self.selection_index = 0

        self.manager.remove(self.main_menu_container)
        self.manager.remove(self.move_menu_container)
        self.manager.remove(self.dialog_menu_container)

        if menu_to_show == "main":
            self.manager.add(self.main_menu_container)
        elif menu_to_show == "moves":
            self.manager.add(self.move_menu_container)
        elif menu_to_show == "dialog":
            self.manager.add(self.dialog_menu_container)

    def updateUiMoves(self):
        moves = self.your_pokemon.moves
        buttons = [self.moveBtn1, self.moveBtn2, self.moveBtn3, self.moveBtn4]

        for i, button in enumerate(buttons):
            if i < len(moves):
                button.text = moves[i]["name"].upper()
                button.on_click = lambda event, move_index=i: self.turn(move_index)
                button.visible = True
                button.enabled = True
            else:
                button.text = ""
                button.visible = False
                button.enabled = False

    def turn(self, moveIndex):
        self.battleState = "currently turn"
        self.switchMenu("dialog")

        enemyMoveIndex = random.randint(0, len(self.enemy_pokemon.moves) - 1)

        if self.your_pokemon.getStat("speed") >= self.enemy_pokemon.getStat("speed"):
            self.turn_queue = [("player", moveIndex), ("enemy", enemyMoveIndex)]
        else:
            self.turn_queue = [("enemy", enemyMoveIndex), ("player", moveIndex)]

        self.execute_next_action()

    def execute_next_action(self):
        if not self.turn_queue:
            self.postTurn()
            return

        attacker_key, move_idx = self.turn_queue.pop(0)

        if attacker_key == "player" and self.your_pokemon.current_hp > 0:
            move_name = self.your_pokemon.moves[move_idx]["name"]
            self.messageQueue.append(f"{self.your_pokemon.name} used {move_name}!")
            result = self.your_pokemon.useMove(move_idx, self.enemy_pokemon)
            self.messageQueue.extend(result)
        elif attacker_key == "enemy" and self.enemy_pokemon.current_hp > 0:
            move_name = self.enemy_pokemon.moves[move_idx]["name"]
            self.messageQueue.append(f"Foe {self.enemy_pokemon.name} used {move_name}!")
            result = self.enemy_pokemon.useMove(move_idx, self.your_pokemon)
            self.messageQueue.extend(result)

        self.nextMessage()

    def nextMessage(self):
        if self.messageQueue:
            self.targetText = self.messageQueue.pop(0)
            self.currentText = ""
            self.isProcessingText = True
        else:
            self.isProcessingText = False

            if self.battleState == "currently turn":
                self.execute_next_action()
            elif self.battleState in ["intro", "post turn"]:
                self.battleState = "waiting"
                arcade.schedule_once(self.resetToMainMenu, 0.5)
            elif self.battleState == "end":
                if self.exp > 0:
                    result = self.your_pokemon.gainExp(self.exp)
                    self.exp = 0

                    if not result["isLeveledUp"] and not result["evolve"]["hasEvolved"]:
                        self.run()

                    if result["isLeveledUp"]:
                        self.player_lvl_label = f"Lv{self.your_pokemon.level}"
                        self.manager.trigger_render()
                        self.messageQueue.extend(
                            [
                                f"{self.your_pokemon.name} has leveled up!!!",
                                f"Now {self.your_pokemon.name} is {self.your_pokemon.level} lvl!!!",
                            ]
                        )
                        self.isProcessingText = True

                    if result["evolve"]["hasEvolved"]:
                        self.hasEvolved = True
                        self.save()
                        self.window.show_view(
                            EvolvingView(
                                self.overworld_view,
                                self.your_pokemon.name.lower(),
                                result["evolve"]["to"],
                            )
                        )
                else:
                    self.run()

    def pokemonDeath(self, diedPokemon: Pokemon):
        self.battleState = "end"
        if diedPokemon.isEnemy:
            self.exp = diedPokemon.getExp()

            self.messageQueue.extend(
                [
                    f"Wild {self.enemy_pokemon.name} fainted!",
                    f"{self.your_pokemon.name} gained {self.exp} EXP. Points!",
                ]
            )

            print(self.messageQueue)

            self.nextMessage()
            self.switchMenu("dialog")
        else:
            self.messageQueue.extend([f"{self.your_pokemon.name} fainted!"])

            self.nextMessage()
            self.switchMenu("dialog")

    def postTurn(self):
        list = []

        list.extend(self.your_pokemon.afterATurn())
        list.extend(self.enemy_pokemon.afterATurn())

        if self.your_pokemon.current_hp <= 0:
            self.pokemonDeath(self.your_pokemon)
            return

        if self.enemy_pokemon.current_hp <= 0:
            self.pokemonDeath(self.enemy_pokemon)
            return

        if len(list) - 1 > 0:
            self.battleState = "post turn"

            self.messageQueue.extend(list)

            self.nextMessage()
            self.switchMenu("dialog")
        else:
            self.battleState = "waiting"
            arcade.schedule_once(self.resetToMainMenu, 0.5)

    def resetToMainMenu(self, dt):
        self.switchMenu("main")
        self.targetText = f"What will {self.your_pokemon.name} do?"
        self.currentText = ""

    def on_draw(self):
        self.clear()

        self.window.default_camera.use()

        self.manager.draw()

        self.enemy_pokemon.draw()
        self.your_pokemon.draw()

        self.drawHpBar(self.your_pokemon, self.hp_bars.get("player"))
        self.drawExpBar()
        self.drawHpBar(self.enemy_pokemon, self.hp_bars.get("enemy"))

        if self.active_menu != "dialog":
            current_list = (
                self.main_buttons if self.active_menu == "main" else self.move_buttons
            )
            active_btn = current_list[self.selection_index]

            self.cursor_text.x = active_btn.rect.left - 10
            self.cursor_text.y = active_btn.rect.center_y
                
            self.cursor_text.draw()

    def on_update(self, delta_time):
        if self.isSliding:
            transitionSpeed = 7

            self.player_hp_widget.center_x -= transitionSpeed
            self.player_lvl_label.center_x -= transitionSpeed
            self.player_name_label.center_x -= transitionSpeed
            self.hp_bars["player"]["x"] -= transitionSpeed
            self.expBar["x"] -= transitionSpeed
            self.your_pokemon.center_x += transitionSpeed
            self.playerPlatform.center_x += transitionSpeed

            self.enemy_hp_widget.center_x += transitionSpeed
            self.enemy_lvl_label.center_x += transitionSpeed
            self.enemy_name_label.center_x += transitionSpeed
            self.hp_bars["enemy"]["x"] += transitionSpeed
            self.enemy_pokemon.center_x -= transitionSpeed
            self.enemyPlatform.center_x -= transitionSpeed

            if self.player_hp_widget.center_x <= self.targetX:
                self.isSliding = False

        self.textDelayTimer += delta_time

        if len(self.currentText) < len(self.targetText):
            if self.textDelayTimer > 0.03:
                self.currentText += self.targetText[len(self.currentText)]
                self.dialog.text = self.currentText
                self.dialogBox.trigger_full_render()
                self.main_menu_container.trigger_full_render()
                self.textDelayTimer = 0
        elif self.isProcessingText:
            if self.textDelayTimer > 1.5:
                self.nextMessage()
                self.textDelayTimer = 0

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int):
        widgets = self.manager.get_widgets_at((x, y))
        moveButtons = [self.moveBtn1, self.moveBtn2, self.moveBtn3, self.moveBtn4]

        for i, button in enumerate(moveButtons):
            if button in widgets:
                self.move_hover(i)
                return

    def on_key_press(self, key, modifiers):
        if self.active_menu == "main":
            current_list = self.main_buttons
            num_buttons = len(current_list)
        else:
            current_list = self.move_buttons
            num_buttons = len(self.your_pokemon.moves)

        if self.is_pressed(CONFIG.controls.up, key):
            if num_buttons > 2:
                self.selection_index = (self.selection_index - 2) % num_buttons

            if self.active_menu == "moves":
                self.move_hover(self.selection_index)
        elif self.is_pressed(CONFIG.controls.down, key):
            if num_buttons > 2:
                self.selection_index = (self.selection_index + 2) % num_buttons

            if self.active_menu == "moves":
                self.move_hover(self.selection_index)
        elif self.is_pressed(CONFIG.controls.left, key):
            self.selection_index = (self.selection_index - 1) % num_buttons

            if self.active_menu == "moves":
                self.move_hover(self.selection_index)
        elif self.is_pressed(CONFIG.controls.right, key):
            self.selection_index = (self.selection_index + 1) % num_buttons

            if self.active_menu == "moves":
                self.move_hover(self.selection_index)

        elif self.is_pressed(CONFIG.controls.interact, key):
            if self.active_menu == "main":
                if self.selection_index == 0:
                    self.switchMenu("moves")
                elif self.selection_index == 3:
                    self.run()
            elif self.active_menu == "moves":
                self.turn(self.selection_index)
            elif self.active_menu == "dialog":
                self.currentText = self.targetText
                self.dialog.text = self.currentText
                self.dialogBox.trigger_full_render()
                self.main_menu_container.trigger_full_render()
                self.textDelayTimer = 0
        elif self.is_pressed(CONFIG.controls.cancel, key):
            if self.active_menu == "moves":
                self.switchMenu("main")

    def is_pressed(self, configKey, key):
        return getattr(arcade.key, configKey, None) == key

    def move_hover(self, index):
        if index is not None:
            move_name = self.your_pokemon.moves[index]["name"]

            move = getAMove(move_name)
            self.type.text = move["type"]
            self.maxPP.text = move["pp"]
            self.currPP.text = self.your_pokemon.moves[index]["pp"]

    def run(self):
        self.window.show_view(self.overworld_view)
        self.save()

    def save(self):
        updateHp(self.your_pokemon.name, self.your_pokemon.current_hp)
        updateMove(self.your_pokemon.name, self.your_pokemon.moves)
        if not self.hasEvolved:
            updateLevel(
                self.your_pokemon.name, self.your_pokemon.level, self.your_pokemon.exp
            )
        else:
            updateLevel(
                self.your_pokemon.name,
                self.your_pokemon.level,
                self.your_pokemon.exp,
                self.your_pokemon.evolution["to"],
            )
