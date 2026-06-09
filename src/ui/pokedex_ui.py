import arcade
import arcade.gui
from arcade import SpriteList
from src.core.data_loader import DataLoader
from src.constants import POKEDEX_UI


# ── List layout constants ──────────────────────────────────────────────────────

_VISIBLE      = 15            # max entries shown at once
_TRACK_COLOR  = (40, 40, 40)  # near-black charcoal  (track line)
_THUMB_COLOR  = (0,  0,  0)   # solid black           (thumb block)
_TRACK_W      = 2             # track line width in pixels
_THUMB_W      = 6             # thumb width (slightly wider than the track)


class PodedexUi:
    """Full Pokédex UI — background, stats, sprite panel and scrollable list."""

    def __init__(
        self,
        data_loader: DataLoader,
        all_pokemon: list[str],
        owned: set[str],
        seen: set[str],
    ):
        self._manager = arcade.gui.UIManager()
        self._manager._pixelated = True
        self.data_loader = data_loader

        self._all_pokemon = all_pokemon
        self._owned = owned
        self._seen = seen
        self._selected = 0
        self._scroll_top = 0

        tilemap = arcade.load_tilemap(POKEDEX_UI)

        # Will be set while iterating the TMX layer
        self._sprite_cx: float = 322.33   # defaults match actual TMX values
        self._sprite_cy: float = 304.67
        self._sprite_box: int = 144

        for obj in tilemap.get_tilemap_layer("pokedex").tiled_objects:
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y
            w = obj.size.width
            h = obj.size.height

            if obj.name == "bg":
                self._manager.add(arcade.gui.UIImage(
                    texture=arcade.load_texture(
                        "assets/ui/sprites/pokedex.png"),
                    x=x, y=y, width=w, height=h,
                ))

            elif obj.name == "seen":
                self._seen_label = arcade.gui.UILabel(
                    text=str(len(seen)),
                    text_color=arcade.color.WHITE,
                    font_name="Pokemon Emerald", font_size=28, align="right",
                    x=x, y=y - h, width=w, height=h,
                )
                self._manager.add(self._seen_label)

            elif obj.name == "own":
                self._own_label = arcade.gui.UILabel(
                    text=str(len(owned)),
                    text_color=arcade.color.WHITE,
                    font_name="Pokemon Emerald", font_size=28, align="right",
                    x=x, y=y - h, width=w, height=h,
                )
                self._manager.add(self._own_label)

            elif obj.name == "pokemon":
                self._pokemon = arcade.gui.UIImage(
                    texture=arcade.load_texture(
                        "assets/sprite/pokemon/question_mark.png"),
                    x=x, y=y, width=w, height=h
                )
                self._manager.add(self._pokemon)
                
            else:
                self._item = {
                    "x": x,
                    "y": y - h,
                    "w": w,
                    "h": h
                }

        # ── Scrollable list entry labels ──────────────────────────────
        self._entry_texts: list[arcade.Text] = []
        for i, name in enumerate(all_pokemon):
            badge = self._status_badge(name)
            label = f"No.{i + 1:0>3}  {badge}  {name.upper()}"
            self._entry_texts.append(arcade.Text(
                label,
                x=self._item["x"], y=0,
                color=arcade.color.BLACK,
                font_size=28,
                font_name="Pokemon Emerald",
            ))

        self._cursor = arcade.Text(
            "▶",
            x=self._item["x"] - 20, y=0,
            color=arcade.color.BLACK,
            font_size=28, font_name="Pokemon Emerald",
        )

        self.select(0)

    # ──────────────────────────────────────────────────────────────────
    # Public navigation API
    # ──────────────────────────────────────────────────────────────────

    def select(self, index: int) -> None:
        self._selected = max(0, min(index, len(self._all_pokemon) - 1))

        # Scroll window: keep selected entry visible
        if self._selected < self._scroll_top:
            self._scroll_top = self._selected
        elif self._selected >= self._scroll_top + _VISIBLE:
            self._scroll_top = self._selected - _VISIBLE + 1

        self._refresh_pokemon_display()

    def move_up(self) -> None:
        self.select(self._selected - 1)

    def move_down(self) -> None:
        self.select(self._selected + 1)

    def get_selected_name(self) -> str:
        return self._all_pokemon[self._selected]

    # ──────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────

    def _status_badge(self, name: str) -> str:
        if name in self._owned:
            return "★"   # ★
        if name in self._seen:
            return "•"   # •
        return "?"

    def _refresh_pokemon_display(self) -> None:
        name = self._all_pokemon[self._selected]
        profile = self.data_loader.getPokemon(name)
        is_known = (name in self._owned) or (name in self._seen)

    def draw(self) -> None:
        self._manager.draw()

        for i in range(_VISIBLE):
            idx = self._scroll_top + i
            if idx >= len(self._entry_texts):
                break
            entry_y = self._item["y"] - i * self._item["h"]
            text = self._entry_texts[idx]
            text.y = entry_y
            text.draw()

        visible_row = self._selected - self._scroll_top
        self._cursor.y = self._item["y"] - visible_row * self._item["h"]
        self._cursor.draw()
