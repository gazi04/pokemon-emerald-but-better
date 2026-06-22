import arcade
import arcade.gui
from src.constants import POKEMON_INFORMATION_UI
from src.model.save.player import PlayerPokemon
from src.model.static.pokemon import PokemonStat
from src.enums.status_effect import StatusEffect
from src.enums.effect_type import EffectType
from src.core.data_loader import DataLoader

_FONT = "Pokemon Emerald"

_TAB_BG = [
    "assets/ui/sprites/pokmon_info.png",
    "assets/ui/sprites/pokemon_stats.png",
    "assets/ui/sprites/pokemon_moves.png",
]


class PokemonInformationUI:
    def __init__(self, pokemon: PlayerPokemon, data_loader: DataLoader):
        self._manager = arcade.gui.UIManager()
        self._manager._pixelated = True

        _profile = data_loader.get_pokemon(pokemon.name)
        if _profile is None:
            raise ValueError(f"No profile found for '{pokemon.name}'")

        self._current_tab = 0
        self._tab: list[list[arcade.Text]] = [[], [], []]
        self._tab_sprites: list[arcade.SpriteList] = [
            arcade.SpriteList(),
            arcade.SpriteList(),
            arcade.SpriteList(),
        ]

        tilemap = arcade.load_tilemap(POKEMON_INFORMATION_UI)

        for obj in tilemap.get_tilemap_layer("static").tiled_objects:
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y
            w, h = obj.size.width, obj.size.height

            if obj.name == "bar":
                self._manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture("assets/ui/sprites/top_bar.png"),
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                    )
                )
            elif obj.name == "bg":
                self._bg_image = arcade.gui.UIImage(
                    texture=arcade.load_texture(_TAB_BG[0]),
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                )
                self._manager.add(self._bg_image)
            elif obj.name == "tab":
                self._tab_label = arcade.gui.UILabel(
                    text="",
                    font_name=_FONT,
                    font_size=40,
                    x=x,
                    y=y - h,
                    width=w,
                    height=h,
                )
                self._manager.add(self._tab_label)

        for obj in tilemap.get_tilemap_layer("profile").tiled_objects:
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y
            w, h = obj.size.width, obj.size.height

            if obj.name == "profile":
                self._manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture(
                            "assets/ui/sprites/pokemon_profile.png"
                        ),
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                    )
                )
            elif obj.name == "pokemon":
                self._manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture(_profile.sprites.front),
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                    )
                )
            elif obj.name == "pokemon_name":
                self._manager.add(
                    arcade.gui.UILabel(
                        text=pokemon.name.upper(),
                        text_color=arcade.color.BLACK,
                        font_name=_FONT,
                        font_size=32,
                        x=x,
                        y=y - h,
                        width=w,
                        height=h,
                    )
                )
            elif obj.name == "pokemon_level":
                self._manager.add(
                    arcade.gui.UILabel(
                        text=f"Lv{pokemon.level}",
                        text_color=arcade.color.BLACK,
                        font_name=_FONT,
                        font_size=28,
                        x=x,
                        y=y - h,
                        width=w,
                        height=h,
                    )
                )

        abilities = _profile.abilities or []
        ability = abilities[0].upper() if abilities else "—"

        _label_map_info = {
            "name": pokemon.name.upper(),
            "abylity_name": ability,
            "ability_description": "—",
        }

        for obj in tilemap.get_tilemap_layer("pokemon_profile").tiled_objects:
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y
            w = obj.size.width
            h = obj.size.height

            if obj.name == "type":
                cursor_x = x
                for type_name in _profile.types or []:
                    sprite = self._make_type_sprite(type_name, cursor_x, y - h / 2, h)
                    self._tab_sprites[0].append(sprite)
                    cursor_x += sprite.width + 8

            else:
                val = _label_map_info.get(obj.name)
                if val is not None:
                    self._tab[0].append(
                        arcade.Text(
                            val,
                            x=x,
                            y=y,
                            color=arcade.color.BLACK,
                            font_size=30,
                            font_name=_FONT,
                            anchor_y="top",
                            width=w,
                            multiline=True,
                        )
                    )

        lvl = pokemon.level

        exp_to_next = max(0, (lvl + 1) ** 3 - pokemon.exp)

        _label_map_stats = {
            "item": "ITEM: NONE",
            "ribbon": "—",
            "exp": "EXP.",
            "exp_count": str(pokemon.exp),
            "exp_needed": "NEXT Lv.",
            "exp_needed_count": str(exp_to_next),
        }

        stats = self._generate_stats(_profile.stats, lvl)

        for obj in tilemap.get_tilemap_layer("pokemon_stats").tiled_objects:
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y
            w = obj.size.width
            h = obj.size.height

            if obj.name in stats:
                self._tab[1].append(
                    arcade.Text(
                        f"{obj.name:<14} {stats[obj.name]}",
                        x=x,
                        y=y,
                        color=arcade.color.BLACK,
                        font_size=30,
                        font_name=_FONT,
                        align="center",
                        anchor_y="top",
                        width=w,
                    )
                )
            else:
                val = _label_map_stats.get(obj.name)
                if val is not None:
                    self._tab[1].append(
                        arcade.Text(
                            val,
                            x=x,
                            y=y,
                            color=arcade.color.BLACK,
                            font_size=23,
                            font_name=_FONT,
                            anchor_y="top",
                            width=w,
                            multiline=False,
                        )
                    )

        self._moves: list[arcade.Text] = []
        self._move_profiles = []  # parallel list of PokemonMove | None
        self._current_move = 0
        move_index = 0

        for obj in tilemap.get_tilemap_layer("pokemon_moves").tiled_objects:
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y
            w = obj.size.width
            h = obj.size.height

            if obj.name == "description":
                self.description = arcade.Text(
                    "Description",
                    x=x,
                    y=y,
                    color=arcade.color.BLACK,
                    font_size=26,
                    font_name=_FONT,
                    anchor_y="top",
                    width=w,
                    multiline=True,
                )
                self._tab[2].append(self.description)
            elif "move" in obj.name and move_index < len(pokemon.moves):
                move_data = pokemon.moves[move_index]
                move_profile = data_loader.get_move(move_data.name)

                type_y = y - h / 2

                if move_profile is not None:
                    type = self._make_type_sprite(move_profile.type, x - 115, type_y, h)
                    self._tab_sprites[2].append(type)

                move_text = arcade.Text(
                    f"{move_data.name.capitalize():<28}{move_data.pp}/{move_profile.pp}",
                    x=x,
                    y=y,
                    color=arcade.color.BLACK,
                    font_size=30,
                    font_name=_FONT,
                    anchor_y="top",
                    width=w,
                )

                self._moves.append(move_text)
                self._move_profiles.append(move_profile)
                self._tab[2].append(move_text)
                move_index += 1

        self._cursor_label = arcade.Text(
            text="▶",
            x=0,
            y=0,
            color=arcade.color.BLACK,
            font_size=33,
            font_name=_FONT,
            anchor_y="top",
        )
        self._tab[2].append(self._cursor_label)
        self._set_cursor(self._current_move)
        self._set_description()

        self._set_tab(0)

    def _generate_stats(self, stats: PokemonStat, lvl: int) -> dict[str, PokemonStat]:
        pokemon_stats = {}

        pokemon_stats["HP"] = self._stat(stats.hp, lvl) + lvl
        pokemon_stats["ATK"] = self._stat(stats.attack, lvl)
        pokemon_stats["DEF"] = self._stat(stats.defence, lvl)
        pokemon_stats["SP.ATK"] = self._stat(stats.special_attack, lvl)
        pokemon_stats["SP.DEF"] = self._stat(stats.special_defence, lvl)
        pokemon_stats["SPD"] = self._stat(stats.speed, lvl)

        return pokemon_stats

    def _stat(self, base: int, lvl: int) -> int:
        return PokemonStat.scaled(base, lvl)

    def _make_type_sprite(
        self, type_name: str, x: float, cy: float, badge_h: float
    ) -> arcade.Sprite:
        path = f"assets/sprite/types/{type_name.lower()}.png"
        tex = arcade.load_texture(path)
        scale = badge_h / tex.height
        sprite = arcade.Sprite(path, scale=scale)
        sprite.left = x
        sprite.center_y = cy
        return sprite

    def next_move(self):
        self._set_cursor(self._current_move + 1)
        self._set_description()

    def prev_move(self):
        self._set_cursor(self._current_move - 1)
        self._set_description()

    def _set_cursor(self, index: int):
        self._current_move = index % len(self._moves)
        move_text = self._moves[self._current_move]

        self._cursor_label.x = move_text.left - 30
        self._cursor_label.y = move_text.y + 5

    def _set_description(self):
        if not hasattr(self, "description") or not self._move_profiles:
            return

        move = self._move_profiles[self._current_move]
        if move is None:
            self.description.text = "—"
            return

        cat = move.category.capitalize()
        power = str(move.power) if move.power else "—"
        acc = f"{move.accuracy}%" if move.accuracy else "—"
        header = f"{cat}   PWR {power}   ACC {acc}"

        effect_lines: list[str] = []
        for eff in move.effects:
            target = "user" if eff.target in ("self",) else "foe"

            if eff.type == EffectType.STAT and eff.stat and eff.change is not None:
                stat_name = eff.stat.replace("_", " ").title()
                if eff.change > 0:
                    verb = "sharply raises" if eff.change >= 2 else "raises"
                else:
                    verb = "harshly lowers" if eff.change <= -2 else "lowers"
                effect_lines.append(f"{verb.capitalize()} the {target}'s {stat_name}.")

            elif eff.type == EffectType.STATUS_CONDITION and eff.condition:
                condition_text = {
                    StatusEffect.POISON: "poisons",
                    StatusEffect.PARALYSIS: "paralyzes",
                    StatusEffect.SLEEP: "puts to sleep",
                    StatusEffect.BURN: "burns",
                    StatusEffect.FREEZE: "freezes",
                }.get(eff.condition, f"inflicts {eff.condition} on")

                chance = eff.chance
                if chance and chance < 100:
                    effect_lines.append(
                        f"May {condition_text} the {target}. ({chance}%)"
                    )
                else:
                    effect_lines.append(f"{condition_text.capitalize()} the {target}.")

        lines = [header] + effect_lines
        self.description.text = "\n".join(lines)

    def get_current_tab(self) -> int:
        return self._current_tab

    def next_tab(self):
        self._set_tab(self._current_tab + 1)

    def prev_tab(self):
        self._set_tab(self._current_tab - 1)

    def _set_tab(self, index: int):
        self._current_tab = index % 3
        self._bg_image.texture = arcade.load_texture(_TAB_BG[self._current_tab])

        if index == 0:
            self._tab_label.text = "Pokemon Info"
        elif index == 1:
            self._tab_label.text = "Pokemon Stats"
        else:
            self._tab_label.text = "Pokemon Moves"

    def draw(self):
        self._manager.draw()
        self._tab_sprites[self._current_tab].draw(pixelated=True)
        for text in self._tab[self._current_tab]:
            text.draw()
