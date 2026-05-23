import arcade
import arcade.gui


class BattleMenuPanel:
    """
    Component to handle the Fight/Bag/Pokemon/Run buttons and nested moves.
    Widgets are added/removed directly to an external UIManager by the orchestrator.
    """
    def __init__(self, bounds: dict, manager: arcade.gui.UIManager):
        self._manager = manager

        self.active_menu = "main"
        self.selection_index = 0

        self.main_widgets = []   # All widgets for the main menu
        self.move_widgets = []   # All widgets for the move menu
        self.main_buttons = []   # Just the interactive buttons (for cursor)
        self.move_buttons = []   # Just the move buttons (for cursor)

        self._build_main_menu(bounds)
        self._build_move_menu(bounds)

        self.cursor_text = arcade.Text(
            "▶",
            0,
            0,
            arcade.color.BLACK,
            font_size=24,
            anchor_y="center",
            font_name="Pokemon Emerald",
        )

    def _build_main_menu(self, bounds: dict):
        if "box" in bounds:
            b = bounds["box"]
            sprite = arcade.load_texture("assets/ui/sprites/box.png")
            self.main_widgets.append(arcade.gui.UIImage(x=b["x"], y=b["y"], width=b["w"], height=b["h"], texture=sprite))

        if "fight" in bounds:
            b = bounds["fight"]
            sprite = arcade.load_texture("assets/ui/sprites/fightButton.png")
            btn = arcade.gui.UITextureButton(x=b["x"], y=b["y"], width=b["w"], height=b["h"], texture=sprite)
            self.main_widgets.append(btn)
            self.main_buttons.append(btn)

        if "bag" in bounds:
            b = bounds["bag"]
            sprite = arcade.load_texture("assets/ui/sprites/bagButton.png")
            btn = arcade.gui.UITextureButton(x=b["x"], y=b["y"], width=b["w"], height=b["h"], texture=sprite)
            self.main_widgets.append(btn)
            self.main_buttons.append(btn)

        if "pokemon" in bounds:
            b = bounds["pokemon"]
            sprite = arcade.load_texture("assets/ui/sprites/pokemonButton.png")
            btn = arcade.gui.UITextureButton(x=b["x"], y=b["y"], width=b["w"], height=b["h"], texture=sprite)
            self.main_widgets.append(btn)
            self.main_buttons.append(btn)

        if "run" in bounds:
            b = bounds["run"]
            sprite = arcade.load_texture("assets/ui/sprites/runButton.png")
            btn = arcade.gui.UITextureButton(x=b["x"], y=b["y"], width=b["w"], height=b["h"], texture=sprite)
            self.main_widgets.append(btn)
            self.main_buttons.append(btn)

    def _build_move_menu(self, bounds: dict):
        if "movesBox" in bounds:
            b = bounds["movesBox"]
            sprite = arcade.load_texture("assets/ui/sprites/movesBox.png")
            self.move_widgets.append(arcade.gui.UIImage(x=b["x"], y=b["y"], width=b["w"], height=b["h"], texture=sprite))

        move_style = {
            "normal": arcade.gui.UIFlatButton.UIStyle(font_size=24, font_name="Pokemon Emerald", font_color=arcade.color.BLACK, bg=arcade.color.WHITE, border_width=0),
            "hover":  arcade.gui.UIFlatButton.UIStyle(font_size=24, font_name="Pokemon Emerald", font_color=arcade.color.GRAY,  bg=arcade.color.WHITE, border_width=0),
            "press":  arcade.gui.UIFlatButton.UIStyle(font_size=22, font_name="Pokemon Emerald", font_color=arcade.color.WHITE, bg=arcade.color.WHITE, border_width=0),
        }

        for i in range(1, 5):
            name = f"move{i}"
            if name in bounds:
                b = bounds[name]
                btn = arcade.gui.UIFlatButton(x=b["x"], y=b["y"] - b["h"], width=b["w"], height=b["h"], style=move_style)
                self.move_widgets.append(btn)
                self.move_buttons.append(btn)

        if "maxPP" in bounds:
            b = bounds["maxPP"]
            self.max_pp_label = arcade.gui.UILabel(x=b["x"], y=b["y"] - b["h"], width=b["w"], height=b["h"], text_color=arcade.color.BLACK, font_name="Pokemon Emerald", font_size=25)
            self.move_widgets.append(self.max_pp_label)

        if "currentPP" in bounds:
            b = bounds["currentPP"]
            self.curr_pp_label = arcade.gui.UILabel(x=b["x"], y=b["y"] - b["h"], width=b["w"], height=b["h"], text_color=arcade.color.BLACK, font_name="Pokemon Emerald", font_size=25)
            self.move_widgets.append(self.curr_pp_label)

        if "type" in bounds:
            b = bounds["type"]
            self.type_label = arcade.gui.UILabel(x=b["x"], y=b["y"] - b["h"], width=b["w"], height=b["h"], text_color=arcade.color.BLACK, font_name="Pokemon Emerald", font_size=25)
            self.move_widgets.append(self.type_label)

    def _show_widgets(self, widgets):
        for w in widgets:
            self._manager.add(w)

    def _hide_widgets(self, widgets):
        for w in widgets:
            self._manager.remove(w)

    def switch_menu(self, menu_type: str):
        self.active_menu = menu_type
        self.selection_index = 0
        self._hide_widgets(self.main_widgets)
        self._hide_widgets(self.move_widgets)

        if menu_type == "main":
            self._show_widgets(self.main_widgets)
        elif menu_type == "moves":
            self._show_widgets(self.move_widgets)

    def hide(self):
        self._hide_widgets(self.main_widgets)
        self._hide_widgets(self.move_widgets)

    def update_move_info(self, type_str: str, curr_pp: int, max_pp: int):
        if hasattr(self, 'type_label'):
            self.type_label.text = type_str
        if hasattr(self, 'curr_pp_label'):
            self.curr_pp_label.text = str(curr_pp)
        if hasattr(self, 'max_pp_label'):
            self.max_pp_label.text = str(max_pp)

    def draw_cursor(self):
        current_list = self.main_buttons if self.active_menu == "main" else self.move_buttons
        if not current_list or self.selection_index >= len(current_list):
            return
        active_btn = current_list[self.selection_index]
        self.cursor_text.x = active_btn.rect.left - 10
        self.cursor_text.y = active_btn.rect.center_y
        self.cursor_text.draw()
