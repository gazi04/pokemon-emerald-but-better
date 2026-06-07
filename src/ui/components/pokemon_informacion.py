import arcade
import arcade.gui
from src.constants import POKEMON_INFORMACION_UI, FONT
from src.model.player import PlayerPokemon
from src.model.pokemon import PokemonProfile

_MAP_H = 600
_FONT = "Pokemon Emerald"

# Right-panel background per tab
_TAB_BG = [
    "assets/ui/sprites/pokmon_info.png",
    "assets/ui/sprites/pokemon_stats.png",
    "assets/ui/sprites/pokemon_moves.png",
]
_TAB_NAMES = ["INFO", "STATS", "MOVES"]


def _ay(tiled_y: float, h: float = 0) -> float:
    """Tiled top-y → Arcade bottom-y."""
    return _MAP_H - tiled_y - h


class PokemonInformacion:
    """
    Renders the full Pokémon info screen.
    Three tabs (INFO / STATS / MOVES) navigated with left / right.
    Call draw() every frame.
    """

    def __init__(self, pokemon: PlayerPokemon, profile: PokemonProfile):
        self.manager = arcade.gui.UIManager()
        self.manager._pixelated = True

        self._current_tab = 0
        # arcade.Text objects shown per tab
        self._tab_texts: list[list[arcade.Text]] = [[], [], []]

        tilemap = arcade.load_tilemap(POKEMON_INFORMACION_UI)

        # ── Static layer — top bar + swappable right-panel bg ─────────
        for obj in tilemap.get_tilemap_layer("static").tiled_objects:
            x = obj.coordinates.x
            y = obj.coordinates.y   # gid: y = bottom in Tiled → arcade bottom
            w, h = obj.size.width, obj.size.height

            if obj.name == "bar":
                self.manager.add(arcade.gui.UIImage(
                    texture=arcade.load_texture("assets/ui/sprites/top_bar.png"),
                    x=x, y=_MAP_H - y, width=w, height=h,
                ))
            elif obj.name == "bg":
                self._bg_image = arcade.gui.UIImage(
                    texture=arcade.load_texture(_TAB_BG[0]),
                    x=x, y=_MAP_H - y, width=w, height=h,
                )
                self.manager.add(self._bg_image)

        # ── Left panel — always visible ───────────────────────────────
        for obj in tilemap.get_tilemap_layer("profile").tiled_objects:
            x = obj.coordinates.x
            y = obj.coordinates.y
            w, h = obj.size.width, obj.size.height

            if obj.name == "profile":
                self.manager.add(arcade.gui.UIImage(
                    texture=arcade.load_texture("assets/ui/sprites/pokemon_profile.png"),
                    x=x, y=_MAP_H - y, width=w, height=h,
                ))
            elif obj.name == "pokemon":
                self.manager.add(arcade.gui.UIImage(
                    texture=arcade.load_texture(profile.sprites.front),
                    x=x, y=_MAP_H - y, width=w, height=h,
                ))
            elif obj.name == "pokemon_name":
                self.manager.add(arcade.gui.UILabel(
                    text=pokemon.name.upper(),
                    text_color=arcade.color.WHITE,
                    font_name=_FONT,
                    font_size=16,
                    x=x, y=_ay(y, h), width=w, height=h,
                ))
            elif obj.name == "pokemon_level":
                self.manager.add(arcade.gui.UILabel(
                    text=f"Lv{pokemon.level}",
                    text_color=arcade.color.WHITE,
                    font_name=_FONT,
                    font_size=14,
                    x=x, y=_ay(y, h), width=w, height=h,
                ))

        # ── Tab 0: INFO (pokemon_profile layer) ───────────────────────
        abilities   = profile.abilities or []
        ability_str = abilities[0].upper() if abilities else "—"
        types_str   = " / ".join(t.upper() for t in (profile.types or []))

        _label_map_info = {
            "type":                types_str,
            "abylity_name":        ability_str,
            "ability_description": "—",
        }

        for obj in tilemap.get_tilemap_layer("pokemon_profile").tiled_objects:
            val = _label_map_info.get(obj.name)
            if val is not None:
                self._tab_texts[0].append(arcade.Text(
                    val,
                    x=obj.coordinates.x,
                    y=_MAP_H - obj.coordinates.y,
                    color=arcade.color.BLACK,
                    font_size=15,
                    font_name=_FONT,
                    anchor_y="top",
                    width=int(obj.size.width),
                    multiline=True,
                ))

        # ── Tab 1: STATS (pokemon_stats layer) ────────────────────────
        bs  = profile.stats
        lvl = pokemon.level

        def _stat(base: int) -> int:
            return ((2 * base * lvl) // 100) + 5

        exp_to_next = max(0, (lvl + 1) ** 3 - pokemon.exp)

        _label_map_stats = {
            "item":            "ITEM: NONE",
            "ribbon":          "—",
            "exp":             "EXP.",
            "exp_count":       str(pokemon.exp),
            "exp_needed":      "NEXT Lv.",
            "exp_needed_count": str(exp_to_next),
        }

        stat_rows = [
            ("ATK",    _stat(bs.attack)),
            ("DEF",    _stat(bs.defence)),
            ("SP.ATK", _stat(bs.special_attack)),
            ("SP.DEF", _stat(bs.special_defence)),
            ("SPD",    _stat(bs.speed)),
        ]

        for obj in tilemap.get_tilemap_layer("pokemon_stats").tiled_objects:
            x  = obj.coordinates.x
            ty = _MAP_H - obj.coordinates.y   # arcade top
            w  = int(obj.size.width)
            h  = int(obj.size.height)

            if obj.name == "stats_1":
                # Render each stat as its own line inside this box
                row_h = h / len(stat_rows)
                for i, (name, val) in enumerate(stat_rows):
                    self._tab_texts[1].append(arcade.Text(
                        f"{name:<7} {val}",
                        x=x,
                        y=ty - i * row_h,
                        color=arcade.color.BLACK,
                        font_size=13,
                        font_name=_FONT,
                        anchor_y="top",
                    ))
            else:
                val = _label_map_stats.get(obj.name)
                if val is not None:
                    self._tab_texts[1].append(arcade.Text(
                        val,
                        x=x,
                        y=ty,
                        color=arcade.color.BLACK,
                        font_size=14,
                        font_name=_FONT,
                        anchor_y="top",
                        width=w,
                        multiline=False,
                    ))

        # ── Tab 2: MOVES (pokemo_moves layer is empty — render manually) ──
        move_panel_x = 300
        move_top_y   = 470

        for i, move in enumerate(pokemon.moves):
            row_y = move_top_y - i * 55
            self._tab_texts[2].append(arcade.Text(
                move.name.upper(),
                x=move_panel_x,
                y=row_y,
                color=arcade.color.BLACK,
                font_size=16,
                font_name=_FONT,
                anchor_y="top",
            ))
            self._tab_texts[2].append(arcade.Text(
                f"PP  {move.pp}",
                x=move_panel_x + 300,
                y=row_y,
                color=arcade.color.BLACK,
                font_size=14,
                font_name=_FONT,
                anchor_y="top",
            ))

        # ── Tab indicator strip inside the top bar ────────────────────
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

        self._arrow_hint = arcade.Text(
            "◀  ▶  to switch tab",
            x=400,
            y=535,
            color=arcade.color.YELLOW,
            font_size=10,
            font_name=_FONT,
            anchor_x="center",
            anchor_y="center",
        )

        self.setTab(0)

    # ── Public API ────────────────────────────────────────────────────

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
        self.manager.draw()
        for text in self._tab_texts[self._current_tab]:
            text.draw()
        for t in self._tab_indicator_texts:
            t.draw()
        self._arrow_hint.draw()
