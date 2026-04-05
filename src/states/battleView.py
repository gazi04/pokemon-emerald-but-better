import arcade
import arcade.gui
from src.entities.pokemon import Pokemon


class BattleView(arcade.View):
    def __init__(self, pokemon_name, pokemon_data, overworld_view):
        super().__init__()
        self.overworld_view = overworld_view

        self.tilemap = arcade.tilemap.load_tilemap(
            "assets/ui/battle/battleUiDesign.tmx"
        )

        arcade.load_font("assets/fonts/pokemon-emerald.otf")

        self.your_pokemon = Pokemon(pokemon_name, pokemon_data, is_enemy=False)
        self.enemy_pokemon = Pokemon(pokemon_name, pokemon_data, is_enemy=True)

        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        self.hp_bars = {}

        
        raw_map_height = self.tilemap.tiled_map.map_size.height * self.tilemap.tiled_map.tile_size.height

        for layer in self.tilemap.tiled_map.layers:
            layer_name = layer.name

            if layer_name == "background":
                continue

            current_layer = self.tilemap.get_tilemap_layer(layer_name)
            
            for obj in current_layer.tiled_objects:
                obj_w = obj.size.width / 32
                obj_h = obj.size.height / 32
                
                arc_x = obj.coordinates.x / 32
                arc_y = (raw_map_height - obj.coordinates.y) / 32

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
                        texture_pressed=sprite
                    )
                    self.manager.add(self.dialogBox)
                    
                elif obj.name == "box":
                    sprite = arcade.load_texture("assets/ui/battle/box.png")
                    self.box = arcade.gui.UITextureButton(
                        x=arc_x,
                        y=arc_y,
                        width=obj_w,
                        height=obj_h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite
                    )
                    self.manager.add(self.box)

                elif obj.name == "fight":
                    sprite = arcade.load_texture("assets/ui/battle/fightButton.png")
                    self.fightBtn = arcade.gui.UITextureButton(
                        x=arc_x,
                        y=arc_y,
                        width=obj_w,
                        height=obj_h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite
                    )
                    self.manager.add(self.fightBtn)
                
                elif obj.name == "run":
                    sprite = arcade.load_texture("assets/ui/battle/runButton.png")
                    self.runBtn = arcade.gui.UITextureButton(
                        x=arc_x,
                        y=arc_y,
                        width=obj_w,
                        height=obj_h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite
                    )
                    self.manager.add(self.runBtn)
                
                elif obj.name == "pokemon":
                    sprite = arcade.load_texture("assets/ui/battle/pokemonButton.png")
                    self.pokemonBtn = arcade.gui.UITextureButton(
                        x=arc_x,
                        y=arc_y,
                        width=obj_w,
                        height=obj_h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite
                    )
                    self.manager.add(self.pokemonBtn)
                    
                elif obj.name == "bag":
                    sprite = arcade.load_texture("assets/ui/battle/bagButton.png")
                    self.bagBtn = arcade.gui.UITextureButton(
                        x=arc_x,
                        y=arc_y,
                        width=obj_w,
                        height=obj_h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite
                    )
                    self.manager.add(self.bagBtn)

                elif obj.name == "player_hp_widget":
                    sprite = arcade.load_texture("assets/ui/battle/playerHpBar.png")
                    self.player_hp_widget = arcade.gui.UITextureButton(
                        x=arc_x,
                        y=arc_y,
                        width=obj_w,
                        height=obj_h,
                        texture=sprite,
                        texture_hovered=sprite,
                        texture_pressed=sprite
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
                        texture_pressed=sprite
                    )
                    self.manager.add(self.enemy_hp_widget)

                # --- UI LABELS (Names and Levels) ---
                elif obj.name == "player_name":
                    self.player_name_label = arcade.gui.UILabel(
                        text=self.your_pokemon.name.upper(),
                        x=arc_x,
                        y=arc_y-obj_h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25
                    )
                    self.manager.add(self.player_name_label)

                elif obj.name == "player_lvl":
                    self.player_lvl_label = arcade.gui.UILabel(
                        text=f"Lv{self.your_pokemon.level}",
                        x=arc_x,
                        y=arc_y-obj_h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25
                    )
                    self.manager.add(self.player_lvl_label)

                elif obj.name == "enemy_name":
                    self.enemy_name_label = arcade.gui.UILabel(
                        text=self.enemy_pokemon.name.upper(),
                        x=arc_x,
                        y=arc_y-obj_h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25
                    )
                    self.manager.add(self.enemy_name_label)

                elif obj.name == "enemy_lvl":
                    self.enemy_lvl_label = arcade.gui.UILabel(
                        text=f"Lv{self.enemy_pokemon.level}",
                        x=arc_x,
                        y=arc_y-obj_h,
                        text_color=arcade.color.BLACK,
                        font_name="Pokemon Emerald",
                        font_size=25
                    )
                    self.manager.add(self.enemy_lvl_label)

                # --- HP BAR FILL AREAS ---
                # These are just data points for the draw_hp_bar method
                elif obj.name == "player_hp_fill":
                    self.hp_bars["player"] = {
                        "x": arc_x,
                        "y": arc_y,
                        "w": obj_w,
                        "h": obj_h,
                    }

                elif obj.name == "enemy_hp_fill":
                    self.hp_bars["enemy"] = {
                        "x": arc_x,
                        "y": arc_y,
                        "w": obj_w,
                        "h": obj_h,
                    }

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

        left_side = bar_data["x"]
        right_side = bar_data["x"] + current_width
        bottom_side = bar_data["y"]
        top_side = bar_data["y"] + bar_data["h"]
        center_x = left_side + (current_width / 2)
        center_y = bottom_side + (bar_data["h"] / 2)

        # Define the full Rect with all required arguments
        hp_rect = arcade.Rect(
            left=left_side,
            right=right_side,
            bottom=bottom_side,
            top=top_side,
            width=current_width,
            height=bar_data["h"],
            x=center_x,
            y=center_y
        )

        # Draw the filled rectangle using the Rect object
        arcade.draw_rect_filled(hp_rect, color=color)

    def on_draw(self):
        self.clear()
        # self.tilemap.get_tilemap_layer("background").draw()

        self.enemy_pokemon.draw()
        self.your_pokemon.draw()

        self.manager.draw()

        self.draw_hp_bar(self.your_pokemon, self.hp_bars.get("player"))
        self.draw_hp_bar(self.enemy_pokemon, self.hp_bars.get("enemy"))

    def on_show_view(self):
        arcade.set_background_color(arcade.color.AMAZON)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            self.window.show_view(self.overworld_view)
