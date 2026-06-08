import arcade
import arcade.gui
from src.constants import POKEMON_INFORMACION_UI, FONT
from src.model.player import PlayerPokemon
from src.model.pokemon import PokemonProfile, PokemonStat

_MAP_H = 600
_FONT = "Pokemon Emerald"

# Right-panel background per tab
_TAB_BG = [
    "assets/ui/sprites/pokmon_info.png",
    "assets/ui/sprites/pokemon_stats.png",
    "assets/ui/sprites/pokemon_moves.png",
]
_TAB_NAMES = ["INFO", "STATS", "MOVES"]


class PokemonInformacion:
    def __init__(self, pokemon: PlayerPokemon, profile: PokemonProfile):
        self._manager = arcade.gui.UIManager()
        self._manager._pixelated = True

        self._current_tab = 0
        self._tab: list[list[arcade.Text]] = [[], [], []]

        tilemap = arcade.load_tilemap(POKEMON_INFORMACION_UI)

        for obj in tilemap.get_tilemap_layer("static").tiled_objects:
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y   
            w, h = obj.size.width, obj.size.height

            if obj.name == "bar":
                self._manager.add(arcade.gui.UIImage(
                    texture=arcade.load_texture("assets/ui/sprites/top_bar.png"),
                    x=x, y=y, width=w, height=h,
                ))
            elif obj.name == "bg":
                self._bg_image = arcade.gui.UIImage(
                    texture=arcade.load_texture(_TAB_BG[0]),
                    x=x, y=y, width=w, height=h,
                )
                self._manager.add(self._bg_image)

        for obj in tilemap.get_tilemap_layer("profile").tiled_objects:
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y
            w, h = obj.size.width, obj.size.height

            if obj.name == "profile":
                self._manager.add(arcade.gui.UIImage(
                    texture=arcade.load_texture("assets/ui/sprites/pokemon_profile.png"),
                    x=x, y=y, width=w, height=h,
                ))
            elif obj.name == "pokemon":
                self._manager.add(arcade.gui.UIImage(
                    texture=arcade.load_texture(profile.sprites.front),
                    x=x, y=y, width=w, height=h,
                ))
            elif obj.name == "pokemon_name":
                self._manager.add(arcade.gui.UILabel(
                    text=pokemon.name.upper(),
                    text_color=arcade.color.BLACK,
                    font_name=_FONT,
                    font_size=32,
                    x=x, y=y - h, width=w, height=h,
                ))
            elif obj.name == "pokemon_level":
                self._manager.add(arcade.gui.UILabel(
                    text=f"Lv{pokemon.level}",
                    text_color=arcade.color.BLACK,
                    font_name=_FONT,
                    font_size=28,
                    x=x, y=y - h, width=w, height=h,
                ))

        abilities = profile.abilities or []
        ability_str = abilities[0].upper() if abilities else "—"
        types_str = " / ".join(t.upper() for t in (profile.types or []))

        _label_map_info = {
            "name": pokemon.name.upper(),
            "type": types_str,
            "abylity_name": ability_str,
            "ability_description": "—",
        }

        for obj in tilemap.get_tilemap_layer("pokemon_profile").tiled_objects:
            val = _label_map_info.get(obj.name)
            if val is not None:
                self._tab[0].append(arcade.Text(
                    val,
                    x=obj.coordinates.x,
                    y=600 - obj.coordinates.y,
                    color=arcade.color.BLACK,
                    font_size=30,
                    font_name=_FONT,
                    anchor_y="top",
                    width=int(obj.size.width),
                    multiline=True,
                ))

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

        stats = self._generate_stats(profile.stats, lvl)

        for obj in tilemap.get_tilemap_layer("pokemon_stats").tiled_objects:
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y
            w = obj.size.width
            h = obj.size.height

            if obj.name in stats:
                self._tab[1].append(arcade.Text(
                    f"{obj.name:<14} {stats[obj.name]}",
                    x=x,
                    y=y,
                    color=arcade.color.BLACK,
                    font_size=30,
                    font_name=_FONT,
                    align="center",
                    anchor_y="top",
                    width=w,
                ))
            else:
                val = _label_map_stats.get(obj.name)
                if val is not None:
                    self._tab[1].append(arcade.Text(
                        val,
                        x=x,
                        y=y,
                        color=arcade.color.BLACK,
                        font_size=23,
                        font_name=_FONT,
                        anchor_y="top",
                        width=w,
                        multiline=False,
                    ))

        # moves

        self._tab_indicator_texts: list[arcade.Text] = []
        for i, name in enumerate(_TAB_NAMES):
            self._tab_indicator_texts.append(arcade.Text(
                name,
                x=320 + i * 110,
                y=555,
                color=arcade.color.WHITE,
                font_size=13,
                font_name=_FONT,
                anchor_y="center",
            ))
            
        self.setTab(0)

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
        return ((2 * base * lvl) // 100) + 5

    def setTab(self, index: int):
        self._current_tab = index % 3
        self._bg_image.texture = arcade.load_texture(_TAB_BG[self._current_tab])

        for i, t in enumerate(self._tab_indicator_texts):
            t.color = arcade.color.YELLOW if i == self._current_tab else arcade.color.WHITE

    def nextTab(self):
        self.setTab(self._current_tab + 1)

    def prevTab(self):
        self.setTab(self._current_tab - 1)

    def draw(self):
        self._manager.draw()
        for text in self._tab[self._current_tab]:
            text.draw()
        for t in self._tab_indicator_texts:
            t.draw()
