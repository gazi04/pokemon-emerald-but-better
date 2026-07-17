import arcade
import arcade.gui
from src.core.data_loader import DataLoader
from src.model.save.player import PlayerPokemon
from src.model.static.pokemon import PokemonStat
from src.tiled import object_layer


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

        for obj in ui_layer.tiled_objects:
            w = obj.size.width
            h = obj.size.height
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y

            if obj.name == "background":
                self._manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture(
                            "assets/ui/sprites/pokemonMenuBg.png"
                        ),
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                    )
                )
            elif obj.name == "tooltip":
                self._tooltip.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture("assets/ui/sprites/box2.png"),
                        x=0,
                        y=0,
                        width=w,
                        height=h,
                    )
                )
            elif obj.name == "pokemon1":
                slot = int(obj.name[-1]) - 1
                button = arcade.gui.UIImage(
                    texture=self._lead_texture, x=x, y=y, width=w, height=h
                )
                self._pokemon_uis[slot]["profile"] = button
                self._manager.add(button)
            elif "pokemon" in obj.name and "pokemonSprite" not in obj.name:
                slot = int(obj.name[-1]) - 1
                button = arcade.gui.UIImage(
                    texture=self._profile_texture, x=x, y=y, width=w, height=h
                )
                self._pokemon_uis[slot]["profile"] = button
                self._manager.add(button)

            elif "pokeball" in obj.name:
                slot = int(obj.name[-1]) - 1
                image = arcade.gui.UIImage(
                    texture=arcade.load_texture(
                        "assets/ui/sprites/pokeballProfile.png"
                    ),
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                )
                self._pokemon_uis[slot]["pokeball"] = image
                self._manager.add(image)
            elif "pokemonSprite" in obj.name:
                slot = int(obj.name[-1]) - 1
                image = arcade.gui.UIImage(
                    texture=arcade.load_texture(
                        "assets/sprite/pokemon/question_mark.png"
                    ),
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                )
                self._pokemon_uis[slot]["pokemon"] = image
                self._manager.add(image)
            elif "hpText" in obj.name:
                slot = int(obj.name[-1]) - 1
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
            elif "levelText" in obj.name:
                slot = int(obj.name[-1]) - 1
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
            elif "nameText" in obj.name:
                slot = int(obj.name[-1]) - 1
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
            elif "hpBar" in obj.name:
                slot = int(obj.name[-1]) - 1
                self._pokemon_uis[slot]["hp_bar"] = {
                    "x": x,
                    "y": y - h,
                    "w": w,
                    "h": h,
                }
            elif obj.name == "box":
                self._manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture("assets/ui/sprites/box.png"),
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                    )
                )
            elif obj.name == "text":
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
                slot["pokemon"].texture = arcade.load_texture(
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
