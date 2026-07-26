import arcade
import arcade.gui
from src.ui.layout_parser import parse_battle_layout
from src.ui.components.typewriter_message_box import TypewriterMessageBox
from src.ui.components.battle_menu_panel import BattleMenuPanel
from src.constants import BATTLE_UI
from src.enums.status_effect import StatusEffect

# Each StatusEffect value maps directly to a sprite file name.
_STATUS_DIR = "assets/sprite/status_effect"
_STATUS_SCALE = 2.0


class BattleUiManager:
    """
    Orchestrator for the Battle UI. Retrieves bounds via layout_parser,
    and initializes/coordinates all visual components.
    """

    def __init__(self, after_text_callback):
        self.bounds = parse_battle_layout(BATTLE_UI)

        self.manager = arcade.gui.UIManager()
        self.manager.enable()
        self.manager._pixelated = True

        # Status-condition icons (poison / paralysis / sleep / burn / freeze)
        self._status_textures = {
            status: arcade.load_texture(f"{_STATUS_DIR}/{status.value}.png")
            for status in StatusEffect
            if status
            not in (StatusEffect.NONE, StatusEffect.FLINCH, StatusEffect.CONFUSION)
        }

        # Static graphics
        self._build_static_graphics()

        # Components
        self.message_box = TypewriterMessageBox(self.bounds, self.manager)
        self.message_box.set_callback(after_text_callback)

        self.menu_panel = BattleMenuPanel(self.bounds, self.manager)

        self.active_component = None

        # HP/Exp
        self.hp_bars = {}
        if "player_hp_fill" in self.bounds:
            b = self.bounds["player_hp_fill"]
            self.hp_bars["player"] = {
                "x": b["x"],
                "y": b["y"] - b["h"],
                "w": b["w"],
                "h": b["h"],
            }
        if "enemy_hp_fill" in self.bounds:
            b = self.bounds["enemy_hp_fill"]
            self.hp_bars["enemy"] = {
                "x": b["x"],
                "y": b["y"] - b["h"],
                "w": b["w"],
                "h": b["h"],
            }

        self.exp_bar = None
        if "player_xp_fill" in self.bounds:
            b = self.bounds["player_xp_fill"]
            self.exp_bar = {"x": b["x"], "y": b["y"] - b["h"], "w": b["w"], "h": b["h"]}

        # Animation state
        self.is_sliding = False
        self.target_x = (
            self.player_hp_widget.center_x if hasattr(self, "player_hp_widget") else 0
        )
        self.your_pokemon = None
        self.enemy_pokemon = None

        self.switch_mode("main")

    def _build_static_graphics(self):
        # Background
        if "background" in self.bounds:
            b = self.bounds["background"]
            sprite = arcade.load_texture("assets/ui/sprites/background.png")
            self.manager.add(
                arcade.gui.UIImage(
                    x=b["x"], y=b["y"], width=b["w"], height=b["h"], texture=sprite
                )
            )

        # Platforms
        if "playerPlatform" in self.bounds:
            b = self.bounds["playerPlatform"]
            self.player_platform = arcade.gui.UIImage(
                x=b["x"],
                y=b["y"],
                width=b["w"],
                height=b["h"],
                texture=arcade.load_texture("assets/ui/sprites/battlePlatform.png"),
            )
            self.manager.add(self.player_platform)

        if "enemyPlatform" in self.bounds:
            b = self.bounds["enemyPlatform"]
            self.enemy_platform = arcade.gui.UIImage(
                x=b["x"],
                y=b["y"],
                width=b["w"],
                height=b["h"],
                texture=arcade.load_texture("assets/ui/sprites/battlePlatform.png"),
            )
            self.manager.add(self.enemy_platform)

        # HP Widgets
        if "player_hp_widget" in self.bounds:
            b = self.bounds["player_hp_widget"]
            self.player_hp_widget = arcade.gui.UIImage(
                x=b["x"],
                y=b["y"],
                width=b["w"],
                height=b["h"],
                texture=arcade.load_texture("assets/ui/sprites/playerHpBar.png"),
            )
            self.manager.add(self.player_hp_widget)

        if "enemy_hp_widget" in self.bounds:
            b = self.bounds["enemy_hp_widget"]
            self.enemy_hp_widget = arcade.gui.UIImage(
                x=b["x"],
                y=b["y"],
                width=b["w"],
                height=b["h"],
                texture=arcade.load_texture("assets/ui/sprites/enemyHpBar.png"),
            )
            self.manager.add(self.enemy_hp_widget)

        # Status Effects
        if "status_effect_player" in self.bounds:
            b = self.bounds["status_effect_player"]
            self.status_effect_player = arcade.gui.UIImage(
                x=b["x"],
                y=b["y"],
                width=b["w"],
                height=b["h"],
                texture=self._status_textures[StatusEffect.BURN],
            )
            self.manager.add(self.status_effect_player)
            self.status_effect_player.visible = False

        if "status_effect_enemy" in self.bounds:
            b = self.bounds["status_effect_enemy"]
            self.status_effect_enemy = arcade.gui.UIImage(
                x=b["x"],
                y=b["y"],
                width=b["w"],
                height=b["h"],
                texture=self._status_textures[StatusEffect.BURN],
            )
            self.manager.add(self.status_effect_enemy)
            self.status_effect_enemy.visible = False

        # Labels
        if "player_name" in self.bounds:
            b = self.bounds["player_name"]
            self.player_name_label = arcade.gui.UILabel(
                x=b["x"],
                y=b["y"] - b["h"],
                text_color=arcade.color.BLACK,
                font_name="Pokemon Emerald",
                font_size=25,
            )
            self.manager.add(self.player_name_label)

        if "player_lvl" in self.bounds:
            b = self.bounds["player_lvl"]
            self.player_level_label = arcade.gui.UILabel(
                x=b["x"],
                y=b["y"] - b["h"],
                text_color=arcade.color.BLACK,
                font_name="Pokemon Emerald",
                font_size=25,
            )
            self.manager.add(self.player_level_label)

        if "enemy_name" in self.bounds:
            b = self.bounds["enemy_name"]
            self.enemy_name_label = arcade.gui.UILabel(
                x=b["x"],
                y=b["y"] - b["h"],
                text_color=arcade.color.BLACK,
                font_name="Pokemon Emerald",
                font_size=25,
            )
            self.manager.add(self.enemy_name_label)

        if "enemy_lvl" in self.bounds:
            b = self.bounds["enemy_lvl"]
            self.enemy_level_label = arcade.gui.UILabel(
                x=b["x"],
                y=b["y"] - b["h"],
                text_color=arcade.color.BLACK,
                font_name="Pokemon Emerald",
                font_size=25,
            )
            self.manager.add(self.enemy_level_label)

        # Dialog box background - always visible (shown in both main and dialog modes)
        if "dialogBox" in self.bounds:
            b = self.bounds["dialogBox"]
            self.manager.add(
                arcade.gui.UIImage(
                    x=b["x"],
                    y=b["y"],
                    width=b["w"],
                    height=b["h"],
                    texture=arcade.load_texture("assets/ui/sprites/dialogbox.png"),
                )
            )

    def switch_mode(self, mode: str):
        self.active_component = mode
        self.menu_panel.hide()
        self.message_box.hide()

        if mode in ("main", "moves"):
            self.menu_panel.switch_menu(mode)
        elif mode == "dialog":
            self.message_box.show()

    def queue_messages(self, messages: list[str]):
        for m in messages:
            self.message_box.queue_message(m)

    # Widgets that sit with the player's Pokémon vs. the enemy's — _shift()
    # moves the two groups by opposite signs so they slide in/out from
    # opposite screen edges.
    _PLAYER_LABEL_WIDGETS = (
        "player_hp_widget",
        "player_level_label",
        "player_name_label",
    )
    _ENEMY_LABEL_WIDGETS = (
        "enemy_hp_widget",
        "enemy_level_label",
        "enemy_name_label",
    )

    def _shift(self, delta: float) -> None:
        """Move every transition-slide element by `delta` (player-side labels/
        bars) or `-delta` (enemy-side, and the platforms/sprites on both
        sides, which slide in from behind their own labels).

        set_transition() calls this once with +800 to push everything to its
        off-screen start position; _process_transition() calls it every frame
        with -speed to ease back to center — same math, opposite direction.
        """
        for name in self._PLAYER_LABEL_WIDGETS:
            widget = getattr(self, name, None)
            if widget:
                widget.center_x += delta
        for name in self._ENEMY_LABEL_WIDGETS:
            widget = getattr(self, name, None)
            if widget:
                widget.center_x -= delta

        if "player" in self.hp_bars:
            self.hp_bars["player"]["x"] += delta
        if "enemy" in self.hp_bars:
            self.hp_bars["enemy"]["x"] -= delta
        if self.exp_bar:
            self.exp_bar["x"] += delta

        if hasattr(self, "player_platform"):
            self.player_platform.center_x -= delta
        if hasattr(self, "enemy_platform"):
            self.enemy_platform.center_x += delta

        if self.your_pokemon:
            self.your_pokemon.center_x -= delta
        if self.enemy_pokemon:
            self.enemy_pokemon.center_x += delta

    def set_transition(
        self, your_pokemon, enemy_pokemon, is_trainer, your_name, enemy_name
    ):
        self.is_sliding = True
        self.your_pokemon = your_pokemon
        self.enemy_pokemon = enemy_pokemon

        if not is_trainer:
            self.queue_messages(
                [
                    f"A foe {enemy_name} appeared!",
                    f"Go! {your_name}!",
                ]
            )
        else:
            self.queue_messages(
                [
                    "A trainer is challenges you!!",
                    f"A foe {enemy_name} appeared!",
                    f"Go! {your_name}!",
                ]
            )

        self.switch_mode("dialog")
        self._shift(800)

    def _process_transition(self):
        if not self.is_sliding:
            return

        self._shift(-7)

        if (
            hasattr(self, "player_hp_widget")
            and self.player_hp_widget.center_x <= self.target_x
        ):
            self.is_sliding = False

    def update(self, delta_time):
        self._process_transition()
        self.message_box.update(delta_time)

    def draw(self):
        self.manager.draw()
        if self.active_component in ("main", "moves"):
            self.menu_panel.draw_cursor()

    # Helpers
    def set_player_info(self, name: str, level: int):
        if hasattr(self, "player_name_label"):
            self.player_name_label.text = name
        if hasattr(self, "player_level_label"):
            self.player_level_label.text = f"Lv{level}"

    def set_enemy_info(self, name: str, level: int):
        if hasattr(self, "enemy_name_label"):
            self.enemy_name_label.text = name
        if hasattr(self, "enemy_level_label"):
            self.enemy_level_label.text = f"Lv{level}"

    def draw_hp_bar(self, ratio: float, target: str):
        if target not in self.hp_bars:
            return
        bar = self.hp_bars[target]
        w = bar["w"] * ratio

        color = arcade.color.GREEN
        if ratio < 0.2:
            color = arcade.color.RED
        elif ratio < 0.5:
            color = arcade.color.GOLD

        arcade.draw_lrbt_rectangle_filled(
            left=bar["x"],
            right=bar["x"] + w,
            bottom=bar["y"],
            top=bar["y"] + bar["h"],
            color=color,
        )

    def draw_status(self, status: StatusEffect, target: str):
        ui = (
            self.status_effect_player
            if target == "player"
            else self.status_effect_enemy
        )

        if not status or status is StatusEffect.NONE:
            ui.visible = False
            return

        texture = self._status_textures.get(status)
        if texture:
            ui.texture = texture
            ui.visible = True

    def draw_exp_bar(self, ratio: float):
        if not self.exp_bar:
            return
        w = self.exp_bar["w"] * ratio
        arcade.draw_lrbt_rectangle_filled(
            left=self.exp_bar["x"],
            right=self.exp_bar["x"] + w,
            bottom=self.exp_bar["y"],
            top=self.exp_bar["y"] + self.exp_bar["h"],
            color=arcade.color.CYAN,
        )
