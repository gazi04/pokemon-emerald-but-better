import arcade
from src.core.data_loader import DataLoader
from src.core.player_manager import PlayerManager
from data.config import Config
from src.states.base_view import GameView
from src.ui.shop_ui import ShopUI

CONFIG = Config.load()


class ShopView(GameView):
    def __init__(
        self,
        overworld: arcade.View,
        previous_view: arcade.View,
        data_loader: DataLoader,
        player_manager: PlayerManager,
    ):
        super().__init__()

        self.overworld = overworld
        self.previous_view = previous_view
        self.player_manager = player_manager

        self.items = data_loader.items
        self._item_names = list(self.items.keys())

        self.ui = ShopUI(self.items)

        self._mode = "options"
        self._option_index = 0
        self._item_index = 0
        self._amount = 1

        self.ui.set_money(self.player_manager.player.money)
        self.ui.select_option(self._option_index)

    def on_draw(self):
        self.clear()
        self.overworld.on_draw()
        arcade.get_window().default_camera.use()
        self.ui.draw()

    def on_key_press(self, key, modifiers):
        if self._mode == "options":
            self._handle_options(key)
        elif self._mode == "items":
            self._handle_items(key)
        elif self._mode == "amount":
            self._handle_amount(key)

    def _handle_options(self, key):
        if self.is_pressed(CONFIG.controls.up, key) or self.is_pressed(
            CONFIG.controls.down, key
        ):
            self._option_index = 1 - self._option_index  # toggle between 0 and 1
            self.ui.select_option(self._option_index)

        elif self.is_pressed(CONFIG.controls.interact, key):
            if self._option_index == 0:
                self._mode = "items"
                self._item_index = 0
                self.ui.show_shop()
                self.ui.selecting_item(self._item_index)
            elif self._option_index == 1:
                self.window.show_view(self.previous_view)

        elif self.is_pressed(CONFIG.controls.cancel, key):
            self.window.show_view(self.previous_view)

    def _handle_items(self, key):
        if self.is_pressed(CONFIG.controls.up, key):
            self._item_index = (self._item_index - 1) % len(self._item_names)
            self.ui.selecting_item(self._item_index)

        elif self.is_pressed(CONFIG.controls.down, key):
            self._item_index = (self._item_index + 1) % len(self._item_names)
            self.ui.selecting_item(self._item_index)

        elif self.is_pressed(CONFIG.controls.interact, key):
            self._amount = 1
            self._mode = "amount"
            item = self.items[self._get_item_name()]

            # Read live: add_item() mutates the player's inventory, so a snapshot
            # taken at view init would show a stale count after a purchase.
            bag_item = self.player_manager.player.items.get(self._get_item_name())

            self.ui.show_amount(bag_item.count if bag_item else 0, 1, item.price)

        elif self.is_pressed(CONFIG.controls.cancel, key):
            self._mode = "options"
            self.ui.show_options()
            self.ui.select_option(self._option_index)

    def _handle_amount(self, key):
        item = self.items[self._get_item_name()]

        if self.is_pressed(CONFIG.controls.up, key):
            max_affordable = self.player_manager.player.money // item.price
            self._amount = min(self._amount + 1, max_affordable)
            self.ui.set_amount(self._amount, self._amount * item.price)

        elif self.is_pressed(CONFIG.controls.down, key):
            self._amount = max(1, self._amount - 1)
            self.ui.set_amount(self._amount, self._amount * item.price)

        elif self.is_pressed(CONFIG.controls.interact, key):
            self._confirm_purchase(item)

        elif self.is_pressed(CONFIG.controls.cancel, key):
            self._mode = "items"
            self.ui.show_shop()
            self.ui.selecting_item(self._item_index)

    def _get_item_name(self):
        return self._item_names[self._item_index]

    def _confirm_purchase(self, item):
        total_cost = item.price * self._amount

        if self.player_manager.player.money >= total_cost:
            name = self._item_names[self._item_index]
            self.player_manager.remove_money(total_cost)
            self.player_manager.add_item(name, self._amount)

            self._mode = "items"
            self._amount = 1
            self.ui.show_shop()
            self.ui.set_money(self.player_manager.player.money)
            self.ui.selecting_item(self._item_index)
        else:
            self._mode = "items"
            self.ui.show_shop()
            self.ui.selecting_item(self._item_index)
