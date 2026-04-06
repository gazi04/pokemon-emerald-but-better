import arcade
import arcade.gui
from src.entities.pokemon import Pokemon
from src.util import getAMove

class BattleView(arcade.View):
    def __init__(self, pokemon_name, pokemon_data, overworld_view):
        super().__init__()
        
        self.overworld_view = overworld_view

        self.tilemap = arcade.tilemap.load_tilemap(
            "assets/ui/battle/battleUiDesign.tmx"
        )
        
        move_button_style = {
            "normal": arcade.gui.UIFlatButton.UIStyle(
                font_size=24,
                font_name="Pokemon Emerald",
                font_color=arcade.color.BLACK,
                bg=arcade.color.WHITE,
                border=arcade.color.WHITE,
                border_width=0
            ),
            "hover": arcade.gui.UIFlatButton.UIStyle(
                font_size=24,
                font_name="Pokemon Emerald",
                font_color=arcade.color.GRAY,
                bg=arcade.color.WHITE,
                border=arcade.color.WHITE,
                border_width=0
            ),
            "press": arcade.gui.UIFlatButton.UIStyle(
                font_size=22,
                font_name="Pokemon Emerald",
                font_color=arcade.color.WHITE,
                bg=arcade.color.WHITE,
                border=arcade.color.WHITE,
                border_width=0
            ),
        }

        arcade.load_font("assets/fonts/pokemon-emerald.otf")

        self.your_pokemon = Pokemon(pokemon_name, pokemon_data, [{"name": "tackle", "pp": 15}], is_enemy=False)
        self.enemy_pokemon = Pokemon(pokemon_name, pokemon_data, [{"name": "tackle", "pp": 15}], is_enemy=True)

        self.manager = arcade.gui.UIManager()
        self.manager.enable()
        self.manager._pixelated = True

        self.main_menu_container = arcade.gui.UIWidget()
        self.move_menu_container = arcade.gui.UIWidget()

        self.hp_bars = {}

        raw_map_height = self.tilemap.tiled_map.map_size.height * self.tilemap.tiled_map.tile_size.height

        for layer in self.tilemap.tiled_map.layers:
            layer_name = layer.name

            current_layer = self.tilemap.get_tilemap_layer(layer_name)

            if layer_name == "background":
                continue

            for obj in current_layer.tiled_objects:
                obj_w = int(obj.size.width / 32)
                obj_h = int(obj.size.height / 32)

                arc_x = int(obj.coordinates.x / 32)
                arc_y = int((raw_map_height - obj.coordinates.y) / 32)

                # --- UI TEXTURES (Buttons/Frames) ---
                if obj.name == "dialogBox":
                    sprite = arcade.load_texture("assets/ui/battle/dialogbox.png")
                    self.dialogBox = arcade.gui.UITextureButton(
                        x=arc_x,
                        y=arc_y,
                        width=obj_w,
                        height=obj_h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite,
                    )
                    self.main_menu_container.add(self.dialogBox)

                elif obj.name == "box":
                    sprite = arcade.load_texture("assets/ui/battle/box.png")
                    self.box = arcade.gui.UITextureButton(
                        x=arc_x,
                        y=arc_y,
                        width=obj_w,
                        height=obj_h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite,
                    )
                    self.main_menu_container.add(self.box)

                elif obj.name == "fight":
                    sprite = arcade.load_texture("assets/ui/battle/fightButton.png")
                    fightBtn = arcade.gui.UITextureButton(
                        x=arc_x,
                        y=arc_y,
                        width=obj_w,
                        height=obj_h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite,
                    )
                    fightBtn.on_click = lambda event: self.switch_menu("moves")

                    self.main_menu_container.add(fightBtn)

                elif obj.name == "run":
                    sprite = arcade.load_texture("assets/ui/battle/runButton.png")
                    runBtn = arcade.gui.UITextureButton(
                        x=arc_x,
                        y=arc_y,
                        width=obj_w,
                        height=obj_h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite,
                    )
                    runBtn.on_click = lambda event: self.run()
                    self.main_menu_container.add(runBtn)

                elif obj.name == "pokemon":
                    sprite = arcade.load_texture("assets/ui/battle/pokemonButton.png")
                    self.pokemonBtn = arcade.gui.UITextureButton(
                        x=arc_x,
                        y=arc_y,
                        width=obj_w,
                        height=obj_h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite,
                    )
                    self.main_menu_container.add(self.pokemonBtn)

                elif obj.name == "bag":
                    sprite = arcade.load_texture("assets/ui/battle/bagButton.png")
                    self.bagBtn = arcade.gui.UITextureButton(
                        x=arc_x,
                        y=arc_y,
                        width=obj_w,
                        height=obj_h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite,
                    )
                    self.main_menu_container.add(self.bagBtn)
                    
                if obj.name == "move1":
                    self.moveBtn1 = arcade.gui.UIFlatButton(
                        x=arc_x,
                        y=arc_y - obj_h,
                        width=obj_w,
                        height=obj_h,
                        style=move_button_style,
                        bg=(255, 255, 255, 255)
                    )
                    self.move_menu_container.add(self.moveBtn1)
                
                if obj.name == "move2":
                    self.moveBtn2 = arcade.gui.UIFlatButton(
                        x=arc_x,
                        y=arc_y - obj_h,
                        width=obj_w,
                        height=obj_h,
                        style=move_button_style
                    )
                    self.move_menu_container.add(self.moveBtn2)
                
                if obj.name == "move3":
                    self.moveBtn3 = arcade.gui.UIFlatButton(
                        x=arc_x,
                        y=arc_y - obj_h,
                        width=obj_w,
                        height=obj_h,
                        style=move_button_style
                    )
                    self.move_menu_container.add(self.moveBtn3)
                
                if obj.name == "move4":
                    self.moveBtn4 = arcade.gui.UIFlatButton(
                        x=arc_x,
                        y=arc_y - obj_h,
                        width=obj_w,
                        height=obj_h,
                        style=move_button_style
                    )
                    self.move_menu_container.add(self.moveBtn4)
                    
                elif obj.name == "movesBox":
                    sprite = arcade.load_texture("assets/ui/battle/movesBox.png")
                    self.move_menu_container.add(
                        arcade.gui.UITextureButton(
                            x=arc_x,
                            y=arc_y,
                            width=obj_w,
                            height=obj_h,
                            texture=sprite,
                            texture_hovered=sprite,
                            texture_pressed=sprite,
                        )
                    )

                elif obj.name == "player_hp_widget":
                    sprite = arcade.load_texture("assets/ui/battle/playerHpBar.png")
                    self.player_hp_widget = arcade.gui.UITextureButton(
                        x=arc_x,
                        y=arc_y,
                        width=obj_w,
                        height=obj_h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite,
                    )
                    self.manager.add(self.player_hp_widget)

                elif obj.name == "enemy_hp_widget":
                    sprite = arcade.load_texture("assets/ui/battle/enemyHpBar.png")
                    self.enemy_hp_widget = arcade.gui.UITextureButton(
                        x=arc_x,
                        y=arc_y,
                        width=obj_w,
                        height=obj_h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite,
                    )
                    self.manager.add(self.enemy_hp_widget)

                # --- UI LABELS (Names and Levels) ---
                elif obj.name == "player_name":
                    self.player_name_label = arcade.gui.UILabel(
                        text=self.your_pokemon.name.upper(),
                        x=arc_x,
                        y=arc_y - obj_h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.manager.add(self.player_name_label)

                elif obj.name == "player_lvl":
                    self.player_lvl_label = arcade.gui.UILabel(
                        text=f"Lv{self.your_pokemon.level}",
                        x=arc_x,
                        y=arc_y - obj_h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.manager.add(self.player_lvl_label)

                elif obj.name == "enemy_name":
                    self.enemy_name_label = arcade.gui.UILabel(
                        text=self.enemy_pokemon.name.upper(),
                        x=arc_x,
                        y=arc_y - obj_h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.manager.add(self.enemy_name_label)

                elif obj.name == "enemy_lvl":
                    self.enemy_lvl_label = arcade.gui.UILabel(
                        text=f"Lv{self.enemy_pokemon.level}",
                        x=arc_x,
                        y=arc_y - obj_h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.manager.add(self.enemy_lvl_label)
                    
                elif obj.name == "maxPP":
                    self.maxPP = arcade.gui.UILabel(
                        x=arc_x,
                        y=arc_y - obj_h,
                        width=obj_w,
                        height=obj_h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.move_menu_container.add(self.maxPP)
                    
                elif obj.name == "currentPP":
                    self.currPP = arcade.gui.UILabel(
                        x=arc_x,
                        y=arc_y - obj_h,
                        width=obj_w,
                        height=obj_h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.move_menu_container.add(self.currPP)
                
                elif obj.name == "type":
                    self.type = arcade.gui.UILabel(
                        x=arc_x,
                        y=arc_y - obj_h,
                        width=obj_w,
                        height=obj_h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25,
                    )
                    self.move_menu_container.add(self.type)

                # --- HP BAR FILL AREAS ---
                # These are just data points for the draw_hp_bar method
                elif obj.name == "player_hp_fill":
                    print(f"Map Height: {raw_map_height}, Obj Y: {obj.coordinates.y}, Calc Y: {int(raw_map_height - obj.coordinates.y - obj.size.height)}")
                    self.hp_bars["player"] = {
                        "x": arc_x,
                        "y": arc_y - obj_h,
                        "w": obj_w,
                        "h": obj_h,
                    }

                elif obj.name == "enemy_hp_fill":
                    self.hp_bars["enemy"] = {
                        "x": arc_x,
                        "y": arc_y - obj_h,
                        "w": obj_w,
                        "h": obj_h,
                    }
                    
        self.switch_menu("main")
        self.update_ui_moves()
        first_move = getAMove(self.your_pokemon.moves[0]["name"])
        
        self.type.text = first_move["type"]
        self.maxPP.text = first_move["maxPP"]
        self.currPP.text = self.your_pokemon.moves[0]["pp"]

    def draw_hp_bar(self, pokemon, bar_data): 
        if not bar_data:
            return

        ratio = pokemon.get_hp_ratio()
        full_width = bar_data["w"]
        current_width = full_width * ratio

        # 2. Set the Color
        color = arcade.color.GREEN
        if ratio < 0.2:
            color = arcade.color.RED
        elif ratio < 0.5:
            color = arcade.color.GOLD

        arcade.draw_lrbt_rectangle_filled(
            left=bar_data["x"], 
            right=bar_data["x"] + current_width, 
            bottom=bar_data["y"], 
            top=bar_data["y"] + bar_data["h"], 
            color=color
        )

    def switch_menu(self, menu_to_show):
        self.manager.remove(self.main_menu_container)
        self.manager.remove(self.move_menu_container)
        
        if menu_to_show == "main":
            self.manager.add(self.main_menu_container)
        elif menu_to_show == "moves":
            self.manager.add(self.move_menu_container)

    def update_ui_moves(self):
        moves = self.your_pokemon.moves
        buttons = [self.moveBtn1, self.moveBtn2, self.moveBtn3, self.moveBtn4]
        
        for i, button in enumerate(buttons):
            if i < len(moves):
                button.text = moves[i]["name"].upper()
                button.visible = True
                button.enabled = True
            else:
                button.text = ""
                button.visible = False
                button.enabled = False
        
    def on_draw(self):
        self.clear()

        self.window.default_camera.use()
        
        self.enemy_pokemon.draw()
        self.your_pokemon.draw()

        self.manager.draw()

        self.draw_hp_bar(self.your_pokemon, self.hp_bars.get("player"))
        self.draw_hp_bar(self.enemy_pokemon, self.hp_bars.get("enemy"))
        
    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int):
        widgets = self.manager.get_widgets_at((x, y))
        move_buttons = [self.moveBtn1, self.moveBtn2, self.moveBtn3, self.moveBtn4]

        for i, button in enumerate(move_buttons):
            if button in widgets:
                self.move_hover(i)
                return

    def on_key_press(self, key, modifiers):
        if key == arcade.key.Z:
            self.switch_menu("main")
            
    def move_hover(self, index):
        if index is not None:
            move_name = self.your_pokemon.moves[index]["name"]
            
            move = getAMove(move_name)
            self.type.text = move["type"]
            self.maxPP.text = move["maxPP"]
            self.currPP.text = self.your_pokemon.moves[index]["pp"]
            
    def run(self):
        self.window.show_view(self.overworld_view)
