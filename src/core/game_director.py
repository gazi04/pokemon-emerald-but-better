"""
The Game Director is the single traffic cop for all view transitions.
It sits just beneath the main window and owns the persistent view cache.

Responsibilities:
  - Hold the Overworld as a singleton (never re-instantiated mid-session)
  - Subscribe to SwapViewEvent, CloseViewEvent, OverlayViewEvent
  - Instantiate transient views (Battle, Evolution) from payload data
  - Stack overlay views (Menu, Bag, PokemonMenu) on top without destroying
    the Overworld's state
"""

import arcade
from typing import Any, cast

from src.core.data_loader import DataLoader
from src.core.save_manager import SaveManager
from src.core.event_bus import global_bus
from src.core.events import SwapViewEvent, CloseViewEvent, OverlayViewEvent


class GameDirector:
    def __init__(self, window: arcade.Window):
        self._window = window
        self._view_cache: dict[str, arcade.View] = {}

        self.save_manager = SaveManager()
        self.data_loader = DataLoader()

        global_bus.subscribe(SwapViewEvent, self._on_swap_view)
        global_bus.subscribe(CloseViewEvent, self._on_close_view)
        global_bus.subscribe(OverlayViewEvent, self._on_overlay_view)

    # ------------------------------------------------------------------
    # Boot
    # ------------------------------------------------------------------

    def start(self):
        """Initialise the Overworld once and show it."""
        overworld = self._get_or_create_overworld()
        self._window.show_view(overworld)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_swap_view(self, event: SwapViewEvent):
        """Full screen takeover — transient views get a fresh instance."""
        if event.target == "overworld":
            self._window.show_view(self._get_or_create_overworld())
            return

        view = self._build_transient_view(event.target, event.payload)
        if view:
            self._window.show_view(view)

    def _on_close_view(self, event: CloseViewEvent):
        """Return to the cached Overworld from any transient view."""
        self._window.show_view(self._get_or_create_overworld())

    def _on_overlay_view(self, event: OverlayViewEvent):
        """Stack a menu view on top of whatever is currently showing."""
        view = self._build_overlay_view(event.target, event.payload)
        if view:
            self._window.show_view(view)

    # ------------------------------------------------------------------
    # View construction
    # ------------------------------------------------------------------

    def _get_or_create_overworld(self) -> arcade.View:
        if "overworld" not in self._view_cache:
            # Import here to avoid circular imports at module level
            from src.states.overworld_view import OverworldView

            self._view_cache["overworld"] = OverworldView(
                self.save_manager, self.data_loader
            )
        return self._view_cache["overworld"]

    def _build_transient_view(self, target: str, payload: dict):
        overworld = self._get_or_create_overworld()

        if target == "battle":
            from src.states.battle_view import BattleView

            return BattleView(
                save_manager=self.save_manager,
                data_loader=self.data_loader,
                overworld_view=overworld,
                foe_pokemon_name=payload["pokemon_name"],
                foe_pokemon_data=payload["pokemon_data"],
                foe_level=payload["pokemon_level"],  # kept for flicker transition only
            )
            
        if target == "battle_trainer":
            from src.states.battle_view import BattleView

            return BattleView(
                save_manager=self.save_manager,
                data_loader=self.data_loader,
                overworld_view=overworld,
                is_trainer=True,
                trainer_data=payload["trainer_data"]
            )

        if target == "evolving":
            from src.states.evolving_view import EvolvingView

            return EvolvingView(
                overworldView=overworld,
                pokemon=payload["pokemon"],
                evolvedPokemon=payload["evolved_pokemon"],
            )

        return None

    def _build_overlay_view(self, target: str, payload: dict):
        overworld = self._get_or_create_overworld()
        save_manager = payload.get("save_manager", self.save_manager)
        data_loader = payload.get("data_loader", self.data_loader)

        if target == "menu":
            from src.states.menu_view import MenuView

            return MenuView(overworld, save_manager, data_loader)
        
        if target == "dialog":
            from src.states.dialog_view import DialogView
            
            return DialogView(
                overworld, 
                data_loader, 
                payload.get("after_text_callback"), 
                payload.get("npc_id", "")
            )
            
        if target == "pokedex":
            from src.states.pokedex_view import PokedexView
            
            return PokedexView(
                previous_window=payload.get("previous_view", overworld),
                save_manager=save_manager,
                data_loader=data_loader
            )

        if target == "bag":
            from src.states.bag_view import BagView

            return BagView(
                previousWindow=payload.get("previous_view", overworld),
                save_manager=save_manager,
                data_loader=data_loader,
                battleSystem=cast(Any, payload.get("battle_system")),
            )

        if target == "pokemon_menu":
            from src.states.pokemon_menu_view import PokemonMenuView

            return PokemonMenuView(
                previousView=payload.get("previous_view", overworld),
                save_manager=save_manager,
                data_loader=data_loader,
                bag=cast(Any, payload.get("bag")),
                itemIndex=payload.get("item_index", 0),
                battleSystem=cast(Any, payload.get("battle_system")),
            )

        if target == "shop":
            from src.states.shop_view import ShopView

            return ShopView(
                overworld=overworld,
                previous_view=payload.get("previous_view", overworld),
                save_manager=save_manager,
                data_loader=data_loader,
            )

        return None
