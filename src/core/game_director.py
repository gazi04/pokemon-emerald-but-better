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

from src.core.event_bus import global_bus
from src.core.events import SwapViewEvent, CloseViewEvent, OverlayViewEvent


class GameDirector:
    def __init__(self, window: arcade.Window):
        self._window = window
        self._view_cache: dict[str, arcade.View] = {}

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

            self._view_cache["overworld"] = OverworldView()
        return self._view_cache["overworld"]

    def _build_transient_view(self, target: str, payload: dict):
        overworld = self._get_or_create_overworld()

        if target == "battle":
            from src.states.battleView import BattleView

            return BattleView(
                pokemon_name=payload["pokemon_name"],
                pokemon_data=payload["pokemon_data"],
                level=payload["pokemon_level"],
                overworld_view=overworld,  # kept for flicker transition only
            )

        if target == "evolving":
            from src.states.evolvingView import EvolvingView

            return EvolvingView(
                overworldView=overworld,
                pokemon=payload["pokemon"],
                evolvedPokemon=payload["evolved_pokemon"],
            )

        return None

    def _build_overlay_view(self, target: str, payload: dict):
        overworld = self._get_or_create_overworld()

        if target == "menu":
            from src.states.menuView import MenuView

            return MenuView(overworld)

        if target == "bag":
            from src.states.bagView import BagView

            return BagView(
                previousWindow=payload.get("previous_view", overworld),
                battleSystem=payload.get("battle_system"),
            )

        if target == "pokemon_menu":
            from src.states.pokemonMenuView import PokemonMenuView

            return PokemonMenuView(
                previousView=payload.get("previous_view", overworld),
                bag=payload.get("bag"),
                itemIndex=payload.get("item_index", 0),
                battleSystem=payload.get("battle_system"),
            )

        return None
