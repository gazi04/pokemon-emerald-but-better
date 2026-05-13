import arcade
import arcade.gui
from src.entities.pokemonSprites import Pokemon
from src.constants import BATTLE_UI, TEXT_DELAY

class BattleUi:
    def __init__(self, afterText:function):
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
        
        self.tilemap = arcade.tilemap.load_tilemap(BATTLE_UI)
        
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
        self.afterText = afterText
        self.isProcessingText = False

        self.hpBars = {}
        self.bagBtn = None
        self.fightBtn = None
        self.pokemonBtn = None
        self.runBtn = None

        rawMapHeight = (
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
                y = int((rawMapHeight - obj.coordinates.y) / 32)

                # --- UI TEXTURES (Buttons/Frames) ---
                if obj.name == "background":
                    sprite = arcade.load_texture("assets/ui/sprites/background.png")

                    self.background = arcade.gui.UIImage(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        texture=sprite,
                    )
                    self.manager.add(self.background)
                elif obj.name == "playerPlatform":
                    sprite = arcade.load_texture("assets/ui/sprites/battlePlatform.png")

                    self.playerPlatform = arcade.gui.UIImage(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        texture=sprite,
                    )
                    self.manager.add(self.playerPlatform)
                elif obj.name == "enemyPlatform":
                    sprite = arcade.load_texture("assets/ui/sprites/battlePlatform.png")

                    self.enemyPlatform = arcade.gui.UIImage(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        texture=sprite,
                    )
                    self.manager.add(self.enemyPlatform)
                elif obj.name == "dialogBox":
                    sprite = arcade.load_texture("assets/ui/sprites/dialogbox.png")
                    self.dialogBox = arcade.gui.UIImage(
                        x=x, y=y, width=w, height=h, texture=sprite
                    )
                    self.main_menu_container.add(self.dialogBox)
                    self.dialog_menu_container.add(self.dialogBox)

                elif obj.name == "box":
                    sprite = arcade.load_texture("assets/ui/sprites/box.png")
                    self.box = arcade.gui.UITextureButton(
                        x=x, y=y, width=w, height=h, texture=sprite
                    )
                    self.main_menu_container.add(self.box)

                elif obj.name == "fight":
                    sprite = arcade.load_texture("assets/ui/sprites/fightButton.png")
                    self.fightBtn = arcade.gui.UITextureButton(
                        x=x, y=y, width=w, height=h, texture=sprite
                    )
                    self.fightBtn.on_click = lambda event: self.switchMenu("moves")

                    self.main_menu_container.add(self.fightBtn)

                elif obj.name == "run":
                    sprite = arcade.load_texture("assets/ui/sprites/runButton.png")
                    self.runBtn = arcade.gui.UITextureButton(
                        x=x, y=y, width=w, height=h, texture=sprite
                    )
                    self.runBtn.on_click = lambda event: self.run()
                    self.main_menu_container.add(self.runBtn)

                elif obj.name == "pokemon":
                    sprite = arcade.load_texture("assets/ui/sprites/pokemonButton.png")
                    self.pokemonBtn = arcade.gui.UITextureButton(
                        x=x, y=y, width=w, height=h, texture=sprite
                    )
                    self.main_menu_container.add(self.pokemonBtn)

                elif obj.name == "bag":
                    sprite = arcade.load_texture("assets/ui/sprites/bagButton.png")
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
                    sprite = arcade.load_texture("assets/ui/sprites/movesBox.png")
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
                    sprite = arcade.load_texture("assets/ui/sprites/playerHpBar.png")
                    self.playerHpWidget = arcade.gui.UIImage(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite,
                    )
                    self.manager.add(self.playerHpWidget)

                elif obj.name == "enemy_hp_widget":
                    sprite = arcade.load_texture("assets/ui/sprites/enemyHpBar.png")
                    self.enemyHpWidget = arcade.gui.UIImage(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite,
                    )
                    self.manager.add(self.enemyHpWidget)

                # --- UI LABELS (Names and Levels) ---
                elif obj.name == "player_name":
                    self.playerNameLabel = arcade.gui.UILabel(
                        x=x,
                        y=y - h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.manager.add(self.playerNameLabel)

                elif obj.name == "player_lvl":
                    self.playerLevelLabel = arcade.gui.UILabel(
                        x=x,
                        y=y - h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.manager.add(self.playerLevelLabel)

                elif obj.name == "enemy_name":
                    self.enemyNameLabel = arcade.gui.UILabel(
                        x=x,
                        y=y - h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.manager.add(self.enemyNameLabel)

                elif obj.name == "enemy_lvl":
                    self.enemyLevelLabel = arcade.gui.UILabel(
                        x=x,
                        y=y - h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.manager.add(self.enemyLevelLabel)

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
                    self.dialogText = arcade.gui.UILabel(
                        x=x,
                        y=y - h,
                        width=w,
                        height=h,
                        text_color=arcade.color.WHITE,
                        font_name="Pokemon Emerald",
                        font_size=25,
                        align="left",
                        multiline=True
                    )
                    self.main_menu_container.add(self.dialogText)
                    self.dialog_menu_container.add(self.dialogText)

                # --- HP BAR FILL AREAS ---
                elif obj.name == "player_hp_fill":
                    self.hpBars["player"] = {
                        "x": x,
                        "y": y - h,
                        "w": w,
                        "h": h,
                    }

                elif obj.name == "enemy_hp_fill":
                    self.hpBars["enemy"] = {
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

        self.mainButtons = [self.fightBtn, self.bagBtn, self.pokemonBtn, self.runBtn]
        self.moveButtons = [self.moveBtn1, self.moveBtn2, self.moveBtn3, self.moveBtn4]

        self.cursorText = arcade.Text(
            "▶",
            0, 0,
            arcade.color.BLACK,
            font_size=24,
            anchor_y="center",
            font_name="Pokemon Emerald"
        )
        
        self.isSliding = False
        self.targetX = self.playerHpWidget.center_x
        self.switchMenu("main")
    
    def update(self, delta_time):
        self.transition()
        self.dialog(delta_time)
     
    def draw(self):
        self.manager.draw()
        
        if self.activeMenu != "dialog":
            currentList = (
                self.mainButtons if self.activeMenu == "main" else self.moveButtons
            )
            active = currentList[self.selectionIndex]

            self.cursorText.x = active.rect.left - 10
            self.cursorText.y = active.rect.center_y

            self.cursorText.draw()
     
    def setTransition(self, yourPokemon:Pokemon, enemyPokemon:Pokemon):
        self.isSliding = True
        self.yourPokemon = yourPokemon
        self.enemyPokemon = enemyPokemon
        
        self.messageQueue = [
            f"A foe {self.yourPokemon.pokemonBattle.name} appeared!",
            f"Go! {self.enemyPokemon.pokemonBattle.name}!",
        ]

        self.nextMessage()
        self.switchMenu("dialog")
        self.playerHpWidget.center_x += 400
        self.playerLevelLabel.center_x += 400
        self.playerNameLabel.center_x += 400
        self.hpBars["player"]["x"] += 400
        self.expBar["x"] += 400
        self.playerPlatform.center_x -= 400
        self.yourPokemon.center_x -= 400

        self.enemyHpWidget.center_x -= 400
        self.enemyLevelLabel.center_x -= 400
        self.enemyNameLabel.center_x -= 400
        self.hpBars["enemy"]["x"] -= 400
        self.enemyPokemon.center_x += 400
        self.enemyPlatform.center_x += 400
        
    def transition(self):
        if self.isSliding:
            transitionSpeed = 7

            self.playerHpWidget.center_x -= transitionSpeed
            self.playerLevelLabel.center_x -= transitionSpeed
            self.playerNameLabel.center_x -= transitionSpeed
            self.hpBars["player"]["x"] -= transitionSpeed
            self.expBar["x"] -= transitionSpeed
            self.yourPokemon.center_x += transitionSpeed
            self.playerPlatform.center_x += transitionSpeed

            self.enemyHpWidget.center_x += transitionSpeed
            self.enemyLevelLabel.center_x += transitionSpeed
            self.enemyNameLabel.center_x += transitionSpeed
            self.hpBars["enemy"]["x"] += transitionSpeed
            self.enemyPokemon.center_x -= transitionSpeed
            self.enemyPlatform.center_x -= transitionSpeed

            if self.playerHpWidget.center_x <= self.targetX:
                self.isSliding = False

    def dialog(self, delta_time):
        self.textDelayTimer += delta_time

        if len(self.currentText) < len(self.targetText):
            if self.textDelayTimer > TEXT_DELAY:
                self.currentText += self.targetText[len(self.currentText)]
                self.dialogText.text = self.currentText
                self.dialogBox.trigger_full_render()
                self.main_menu_container.trigger_full_render()
                self.textDelayTimer = 0
        elif self.isProcessingText:
            if self.textDelayTimer > 1.5:
                self.nextMessage()
                self.textDelayTimer = 0

    def nextMessage(self):
        if self.messageQueue:
            self.targetText = self.messageQueue.pop(0)
            self.currentText = ""
            self.isProcessingText = True
        else:
            self.isProcessingText = False

            self.afterText()

    def drawHpBar(self, ratio:float, target:str):
        barData = self.hpBars[target]

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

    def drawExpBar(self, ratio:float):
        if not self.expBar:
            return

        fullWidth = self.expBar["w"]
        currentWidth = fullWidth * ratio

        arcade.draw_lrbt_rectangle_filled(
            left=self.expBar["x"],
            right=self.expBar["x"] + currentWidth,
            bottom=self.expBar["y"],
            top=self.expBar["y"] + self.expBar["h"],
            color=arcade.color.CYAN,
        )

    def setMoveInformation(self, type:str, pp:int, maxPp: int):
        self.type.text = type
        self.maxPP.text = maxPp
        self.currPP.text = pp

    def setPlayerInformation(self, name:str, level:int):
        self.playerNameLabel.text = name
        self.playerLevelLabel.text = f"Lv{level}"

    def setEnemyInformation(self, name:str, level:int):
        self.enemyNameLabel.text = name
        self.enemyLevelLabel.text = f"Lv{level}"

    def switchMenu(self, menuToShow):
        self.activeMenu = menuToShow
        self.selectionIndex = 0

        self.manager.remove(self.main_menu_container)
        self.manager.remove(self.move_menu_container)
        self.manager.remove(self.dialog_menu_container)

        if menuToShow == "main":
            self.manager.add(self.main_menu_container)
        elif menuToShow == "moves":
            self.manager.add(self.move_menu_container)
        elif menuToShow == "dialog":
            self.manager.add(self.dialog_menu_container)