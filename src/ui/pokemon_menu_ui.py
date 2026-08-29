import arcade
import arcade.gui
from src.core.data_loader import DataLoader
from src.model.save.player import PlayerPokemon
from src.model.static.pokemon import PokemonStat
from src.tiled import object_layer
from src.assets import load_sprite_texture


class PokemonMenuUi:
    def __init__(self, data_loader: DataLoader):
        self.data_loader = data_loader

        self._manager = arcade.gui.UIManager()
        self._manager._pixelated = True

        tilemap = arcade.load_tilemap("assets/ui/pokemonMenuUiDesign.tmx")
        ui_layer = object_layer(tilemap, "ui")

        self._profile_texture = arcade.load_texture(
            "assets/ui/sprites/pokemonProfile.png"
        )
        self._profile_selected_texture = arcade.load_texture(
            "assets/ui/sprites/pokemonProfileSelected.png"
        )
        self._lead_texture = arcade.load_texture("assets/ui/sprites/pokemonLead.png")
        self._lead_selected_texture = arcade.load_texture(
            "assets/ui/sprites/pokemonLeadSelected.png"
        )
        self._empty_texture = arcade.load_texture("assets/ui/sprites/emptyProfile.png")

        self._pokemon_uis = [{} for _ in range(6)]

        self._tooltip = arcade.gui.UIWidget()
        self._tooltip.visible = False
        self._tooltip_buttons = []

        self._build_ui_layer(ui_layer)

        self._manager.add(self._tooltip)

        self._cursor_text = arcade.Text(
            "▶",
            0,
            0,
            arcade.color.RED,
            font_size=12,
            anchor_y="center",
            font_name="Pokemon Emerald",
        )

    @staticmethod
    def _slot_index(obj_name: str) -> int:
        """Party-slot object names end in a 1-based digit ('pokemon3',
        'hpText3', ...) — every per-slot widget is keyed by that index."""
        return int(obj_name[-1]) - 1

    def _build_ui_layer(self, ui_layer):
        for obj in ui_layer.tiled_objects:
            w = obj.size.width
            h = obj.size.height
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y

            if obj.name == "background":
                self._add_background(x, y, w, h)
            elif obj.name == "tooltip":
                self._add_tooltip_box(w, h)
            elif "pokemon" in obj.name and "pokemonSprite" not in obj.name:
                self._add_profile_button(obj.name, x, y, w, h)
            elif "pokeball" in obj.name:
                self._add_pokeball(obj.name, x, y, w, h)
            elif "pokemonSprite" in obj.name:
                self._add_pokemon_sprite(obj.name, x, y, w, h)
            elif "hpText" in obj.name:
                self._add_hp_text(obj.name, x, y, w, h)
            elif "levelText" in obj.name:
                self._add_level_text(obj.name, x, y, w, h)
            elif "nameText" in obj.name:
                self._add_name_text(obj.name, x, y, w, h)
            elif "hpBar" in obj.name:
                self._add_hp_bar_bounds(obj.name, x, y, w, h)
            elif obj.name == "box":
                self._add_box(x, y, w, h)
            elif obj.name == "text":
                self._add_choose_text(x, y, w, h)

    def _add_background(self, x, y, w, h):
        self._manager.add(
            arcade.gui.UIImage(
                texture=arcade.load_texture("assets/ui/sprites/pokemonMenuBg.png"),
                x=x,
                y=y,
                width=w,
                height=h,
            )
        )

    def _add_tooltip_box(self, w, h):
        self._tooltip.add(
            arcade.gui.UIImage(
                texture=arcade.load_texture("assets/ui/sprites/box2.png"),
                x=0,
                y=0,
                width=w,
                height=h,
            )
        )

    def _add_profile_button(self, obj_name, x, y, w, h):
        """'pokemon1' (the lead slot) gets the lead texture; every other slot
        gets the plain profile texture — same widget otherwise."""
        slot = self._slot_index(obj_name)
        texture = self._lead_texture if slot == 0 else self._profile_texture
        button = arcade.gui.UIImage(texture=texture, x=x, y=y, width=w, height=h)
        self._pokemon_uis[slot]["profile"] = button
        self._manager.add(button)

    def _add_pokeball(self, obj_name, x, y, w, h):
        slot = self._slot_index(obj_name)
        image = arcade.gui.UIImage(
            texture=arcade.load_texture("assets/ui/sprites/pokeballProfile.png"),
            x=x,
            y=y,
            width=w,
            height=h,
        )
        self._pokemon_uis[slot]["pokeball"] = image
        self._manager.add(image)

    def _add_pokemon_sprite(self, obj_name, x, y, w, h):
        slot = self._slot_index(obj_name)
        image = arcade.gui.UIImage(
            texture=arcade.load_texture("assets/sprite/pokemon/question_mark.png"),
            x=x,
            y=y,
            width=w,
            height=h,
        )
        self._pokemon_uis[slot]["pokemon"] = image
        self._manager.add(image)

    def _add_hp_text(self, obj_name, x, y, w, h):
        slot = self._slot_index(obj_name)
        text = arcade.gui.UILabel(
            text="50/50",
            text_color=arcade.color.WHITE,
            font_name="Pokemon Emerald",
            font_size=15,
            align="right",
            x=x,
            y=y - h,
            width=w,
            height=h,
        )
        self._pokemon_uis[slot]["hp_text"] = text
        self._manager.add(text)

    def _add_level_text(self, obj_name, x, y, w, h):
        slot = self._slot_index(obj_name)
        text = arcade.gui.UILabel(
            text="Lv99",
            text_color=arcade.color.WHITE,
            font_name="Pokemon Emerald",
            font_size=15,
            x=x,
            y=y - h,
            width=w,
            height=h,
        )
        self._pokemon_uis[slot]["level_text"] = text
        self._manager.add(text)

    def _add_name_text(self, obj_name, x, y, w, h):
        slot = self._slot_index(obj_name)
        text = arcade.gui.UILabel(
            text="Unknown",
            text_color=arcade.color.WHITE,
            font_name="Pokemon Emerald",
            font_size=15,
            x=x,
            y=y - h,
            width=w,
            height=h,
        )
        self._pokemon_uis[slot]["name_text"] = text
        self._manager.add(text)

    def _add_hp_bar_bounds(self, obj_name, x, y, w, h):
        slot = self._slot_index(obj_name)
        self._pokemon_uis[slot]["hp_bar"] = {"x": x, "y": y - h, "w": w, "h": h}

    def _add_box(self, x, y, w, h):
        self._manager.add(
            arcade.gui.UIImage(
                texture=arcade.load_texture("assets/ui/sprites/box.png"),
                x=x,
                y=y,
                width=w,
                height=h,
            )
        )

    def _add_choose_text(self, x, y, w, h):
        self._manager.add(
            arcade.gui.UILabel(
                text="Choose Pokemon",
                text_color=arcade.color.BLACK,
                font_name="Pokemon Emerald",
                font_size=25,
                x=x,
                y=y - h,
                width=w,
                height=h,
            )
        )

    def setup_tooltip(self, options: list[str]):
        for button in self._tooltip_buttons:
            self._tooltip.remove(button)

        self._tooltip_buttons = []

        for i, option in enumerate(options):
            button = arcade.gui.UILabel(
                text=option,
                text_color=arcade.color.BLACK,
                font_name="Pokemon Emerald",
                font_size=15,
                x=0,
                y=(i * 20) + 5,
                width=self._tooltip.children[0].width - 10,
                height=20,
            )
            self._tooltip.add(button)
            self._tooltip_buttons.append(button)

    def set_values(self, pokemons: list[PlayerPokemon]):
        SKIP_KEYS = {"hp_bar", "profile"}

        for i, slot in enumerate(self._pokemon_uis):
            if i < len(pokemons):
                pokemon = pokemons[i]
                pokemon_profile = self.data_loader.require_pokemon(pokemon.name)
                max_hp = PokemonStat.max_hp(pokemon_profile.stats.hp, pokemon.level)

                slot["name_text"].text = pokemon.name.upper()
                slot["level_text"].text = f"Lv{pokemon.level}"
                slot["hp_text"].text = f"{pokemon.hp}/{max_hp}"
                slot["pokemon"].texture = load_sprite_texture(
                    pokemon_profile.sprites.front
                )

                for key, element in slot.items():
                    if key not in SKIP_KEYS:
                        element.visible = True

                if i == 0:
                    slot["profile"].texture = self._lead_texture
                else:
                    slot["profile"].texture = self._profile_texture
            else:
                for key, element in slot.items():
                    if key not in SKIP_KEYS:
                        element.visible = False

                slot["profile"].texture = self._empty_texture

        self.select_pokemon(0)

    def select_pokemon(self, index: int):
        for i, ui in enumerate(self._pokemon_uis):
            if ui["profile"].texture == self._empty_texture:
                continue

            if i == index:
                ui["profile"].texture = (
                    self._lead_selected_texture
                    if i == 0
                    else self._profile_selected_texture
                )
            else:
                ui["profile"].texture = (
                    self._lead_texture if i == 0 else self._profile_texture
                )

            for key, element in ui.items():
                if key != "hp_bar":
                    self._manager.remove(element)
                    self._manager.add(element)

    def is_tooltip_showing(self) -> bool:
        return bool(self._tooltip.visible)

    def select_tooltip_option(self, index: int):
        self._cursor_text.x = (
            self._tooltip_buttons[len(self._tooltip_buttons) - 1 - index].rect.left - 10
        )
        self._cursor_text.y = self._tooltip_buttons[
            len(self._tooltip_buttons) - 1 - index
        ].rect.center_y

    def show_tooltip(self, index: int):
        self._tooltip.visible = True
        self._cursor_text.visible = True

        for i, element in enumerate(self._tooltip.children):
            x = (
                self._pokemon_uis[index]["profile"].rect.right
                if index == 0
                else self._pokemon_uis[index]["profile"].rect.left
            )

            x += (
                (element.width // 2) + 5 + (15 if i > 0 else 0)
                if index == 0
                else -(element.width // 2) - 5 + (5 if i > 0 else 0)
            )

            element.center_x = x
            element.center_y = (
                self._pokemon_uis[index]["profile"].rect.center_y
                + (element.height * i)
                + 5
            )

        self.select_tooltip_option(0)

    def hide_tooltip(self):
        self._tooltip.visible = False
        self._cursor_text.visible = False

    def draw_hp_bars(self, pokemons: list[PlayerPokemon]):
        for i, pokemon in enumerate(pokemons):
            pokemon_profile = self.data_loader.require_pokemon(pokemon.name)
            max_hp = PokemonStat.max_hp(pokemon_profile.stats.hp, pokemon.level)

            self._draw_hp_bar(pokemon.hp / max_hp, i)

    def _draw_hp_bar(self, ratio: float, index: int):
        bar_data = self._pokemon_uis[index]["hp_bar"]

        full_width = bar_data["w"]
        current_width = full_width * ratio

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
            color=color,
        )

    def draw(self):
        self._manager.draw()
        self._cursor_text.draw()
