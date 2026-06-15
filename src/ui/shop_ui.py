import arcade
import arcade.gui
from src.model.item import Item
from src.constants import SHOP_UI

FONT         = "Pokemon Emerald"
FONT_SIZE    = 26
TEXT_COLOR   = arcade.color.BLACK

class ShopUI:
    def __init__(self, items: dict[str, Item]):
        self._manager = arcade.gui.UIManager()
        self._manager._pixelated = True

        tilemap  = arcade.load_tilemap(SHOP_UI)
        ui_layer = tilemap.get_tilemap_layer("ui")

        self._amount_widget = arcade.gui.UIWidget()
        self._box_amount_widget = arcade.gui.UIWidget()
        self._options_widget = arcade.gui.UIWidget()
        self._shop_widget = arcade.gui.UIWidget()

        self.items = items
        self._item_names = list(items.keys())
        self._item_labels = []  
        self._cursor_index = 0

        for obj in ui_layer.tiled_objects:
            w = obj.size.width
            h = obj.size.height
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y

            if obj.name == "text_box": 
                self._shop_widget.add(self._make_image("assets/ui/sprites/box.png", x, y, w, h))
            elif obj.name == "items_container":
                self._shop_widget.add(self._make_image("assets/ui/sprites/box2.png", x, y, w, h))
            elif obj.name == "option_box":
                self._options_widget.add(self._make_image("assets/ui/sprites/box.png", x, y, w, h))
            elif obj.name == "box_amount_box":
                self._box_amount_widget.add(self._make_image("assets/ui/sprites/box.png", x, y, w, h))
            elif obj.name == "amount_box":
                self._amount_widget.add(self._make_image("assets/ui/sprites/box.png", x, y, w, h))
            elif obj.name == "money_box":
                self._manager.add(self._make_image("assets/ui/sprites/box.png", x, y, w, h))
            elif obj.name == "place_holder":
                self._option_size = {
                    "x": x,
                    "y": y - h, 
                    "w": w,
                    "h": h
                }
            elif obj.name == "item":
                self._item_size = {
                    "x": x,
                    "y": y,
                    "w": w,
                    "h": h
                }

        for obj in ui_layer.tiled_objects:
            w = obj.size.width
            h = obj.size.height
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y

            if obj.name == "money_text":
                self._money_text = self._make_label("", x, y, h, w)
                self._manager.add(self._money_text)
            elif obj.name == "box_amount_text":
                self._box_amount_text = self._make_label("TEST", x, y, h, w)
                self._box_amount_widget.add(self._box_amount_text)
            elif obj.name == "amount_text":
                self._amount_text = self._make_label("TEST", x, y, h, w)
                self._amount_widget.add(self._amount_text)
            elif obj.name == "text":
                self._text = arcade.gui.UILabel(
                    text="",
                    text_color=TEXT_COLOR,
                    font_name=FONT,
                    font_size=FONT_SIZE,
                    x=x, y=y - h,
                    width=w, height=h, multiline=True
                )
                self._shop_widget.add(self._text)

        self._build_item_labels()

        self._cursor = arcade.Text(
            "▶", x=0, y=0,
            color=TEXT_COLOR,
            font_size=FONT_SIZE,
            font_name=FONT,
        )

        self._option_labels = []
        self._build_option_labels(["BUY", "EXIT"])
        self.show_options()

    # ── Builders ──────────────────────────────────────────────────────────────

    def _build_item_labels(self):
        for i, item in enumerate(self._item_names):
            item_data = self.items[item]
            label = self._make_label(
                f"{item.upper():<7} ${item_data.price}",
                self._item_size["x"],
                self._item_size["y"] - i * (self._item_size["h"] + 5),
                self._item_size["h"],
                self._item_size["w"],
            )
            self._item_labels.append(label)
            self._shop_widget.add(label)

    def _build_option_labels(self, options: list[str]):
        for i, option in enumerate(options):
            label = self._make_label(
                option,
                self._option_size["x"],
                self._option_size["y"] - i * (self._option_size["h"] + 5),
                self._option_size["h"],
                self._item_size["w"],
            )
            self._option_labels.append(label)
            self._options_widget.add(label)

    def _make_image(self, path: str, x, y, w, h) -> arcade.gui.UIImage:
        return arcade.gui.UIImage(
            texture=arcade.load_texture(path),
            x=x, y=y, width=w, height=h,
        )

    def _make_label(self, text: str, x, y, h, w) -> arcade.gui.UILabel:
        return arcade.gui.UILabel(
            text=text,
            text_color=TEXT_COLOR,
            font_name=FONT,
            font_size=FONT_SIZE,
            x=x, y=y - h,
            width=w
        )

    def show_options(self):
        self._manager.add(self._options_widget)
        
        self._manager.remove(self._shop_widget)
        self._manager.remove(self._amount_widget)
        self._manager.remove(self._box_amount_widget)

    def show_shop(self):
        """Show the main shop item list."""
        self._manager.add(self._shop_widget)
        
        self._manager.remove(self._options_widget)
        self._manager.remove(self._amount_widget)
        self._manager.remove(self._box_amount_widget)

    def show_amount(self, amount_in_bag: int, amount: int, price: int):
        """Show the quantity selector (after picking an item to buy)."""
        self._box_amount_text.text = f"In Bag: {amount_in_bag}"
        self._amount_text.text = f"x{amount} ${price}"
        
        self._manager.add(self._box_amount_widget)
        self._manager.add(self._amount_widget)
        
    def set_money(self, money: int):
        self._money_text.text = f"${money}"

    def set_amount(self, amount: int, price: int):
        self._amount_text.text = f"x{amount} ${price}"

    def selecting_item(self, index: int):
        if index < len(self.items):
            name = self._item_names[index]
            item = self.items[name]
            self._text.text = item.description
            self._update_cursor(index)

    def select_option(self, index: int):
        self._update_cursor(index, use_options=True)

    def _update_cursor(self, index: int, use_options: bool = False):
        if use_options:
            label = self._option_labels[index]
        else:
            label = self._item_labels[index]

        self._cursor.x = label.rect.left - 20
        self._cursor.y = label.rect.center_y - 10

    def draw(self):
        self._manager.draw()
        self._cursor.draw()