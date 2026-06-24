import arcade
import arcade.gui
from src.core.data_loader import DataLoader
from src.constants import POKEDEX_UI


class PokedexUi:
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

        self._visible = 15
        self._middle_row = self._visible // 2

        tilemap = arcade.load_tilemap(POKEDEX_UI)

        for obj in tilemap.get_tilemap_layer("pokedex").tiled_objects:
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y
            w = obj.size.width
            h = obj.size.height

            if obj.name == "bg":
                self._manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture("assets/ui/sprites/pokedex.png"),
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                    )
                )

            elif obj.name == "seen":
                self._seen_label = arcade.gui.UILabel(
                    text=str(len(seen)),
                    text_color=arcade.color.WHITE,
                    font_name="Pokemon Emerald",
                    font_size=28,
                    align="right",
                    x=x,
                    y=y - h,
                    width=w,
                    height=h,
                )
                self._manager.add(self._seen_label)

            elif obj.name == "own":
                self._own_label = arcade.gui.UILabel(
                    text=str(len(owned)),
                    text_color=arcade.color.WHITE,
                    font_name="Pokemon Emerald",
                    font_size=28,
                    align="right",
                    x=x,
                    y=y - h,
                    width=w,
                    height=h,
                )
                self._manager.add(self._own_label)

            elif obj.name == "pokemon":
                self._pokemon = arcade.gui.UIImage(
                    texture=arcade.load_texture(
                        "assets/sprite/pokemon/question_mark.png"
                    ),
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                )
                self._manager.add(self._pokemon)

            else:
                self._item_structure = {
                    "x": x,
                    "top": 526,
                    "middle": y - h,
                    "w": w,
                    "h": h,
                }
                self._list_top = 526
                self._list_bottom = 74

        self._entry_texts: list[arcade.Text] = []
        for i, name in enumerate(all_pokemon):
            badge = self._status_badge(name)
            if badge != "?":
                label = f"No.{i + 1:0>3}  {badge}  {name.upper()}"
            else:
                label = f"No.{i + 1:0>3}  ------------"

            self._entry_texts.append(
                arcade.Text(
                    label,
                    x=self._item_structure["x"],
                    y=0,
                    color=arcade.color.BLACK,
                    font_size=28,
                    font_name="Pokemon Emerald",
                )
            )

        self._cursor = arcade.Text(
            "▶",
            x=self._item_structure["x"] - 20,
            y=self._item_structure["middle"],
            color=arcade.color.BLACK,
            font_size=28,
            font_name="Pokemon Emerald",
        )

        self._select(0)

    def move_up(self) -> None:
        self._select(self._selected - 1)

    def move_down(self) -> None:
        self._select(self._selected + 1)

    def _select(self, index: int) -> None:
        self._selected = max(0, min(index, len(self._all_pokemon) - 1))

        self._scroll_top = self._selected - self._middle_row
        max_scroll = max(0, len(self._all_pokemon) - self._visible)
        self._scroll_top = max(0, min(self._scroll_top, max_scroll))

        self._refresh_pokemon_display()

    def _status_badge(self, name: str) -> str:
        if name in self._owned:
            return "★"
        if name in self._seen:
            return "•"
        return "?"

    def _refresh_pokemon_display(self) -> None:
        name = self._all_pokemon[self._selected]
        is_known = name in self._owned or name in self._seen

        if is_known:
            profile = self.data_loader.get_pokemon(name)
            texture = arcade.load_texture(profile.sprites.front)
        else:
            texture = arcade.load_texture("assets/sprite/pokemon/question_mark.png")

        self._pokemon.texture = texture
        self._manager.trigger_render()

    def draw(self) -> None:
        self._manager.draw()

        middle_y = self._item_structure["middle"]
        row_h = self._item_structure["h"]

        for i in range(self._visible):
            index = self._scroll_top + i
            if index >= len(self._entry_texts):
                break

            row_offset = i - (self._selected - self._scroll_top)
            entry_y = middle_y - row_offset * row_h

            if entry_y > self._list_top or entry_y < self._list_bottom:
                continue

            self._entry_texts[index].y = entry_y
            self._entry_texts[index].draw()

        self._cursor.draw()
