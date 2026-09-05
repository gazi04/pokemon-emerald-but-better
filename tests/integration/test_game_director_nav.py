"""
Integration test: GameDirector's event-driven navigation wiring.

GameDirector is the single traffic cop for view transitions (see
src/core/game_director.py). Nothing previously exercised it — this covers
the wiring itself (event -> builder -> constructor kwargs -> window.show_view),
using dummy arcade.View subclasses in place of the real heavy views (which
need real map/sprite/pokemon data to construct). The real view classes are
tested for their own behavior elsewhere; here we only verify GameDirector
picks the right one and threads payload data through correctly.
"""

import arcade
import pytest

# Import every view module GameDirector can build *before* any fixture chdir's
# into a tmp data dir — these modules read `data/config.json` relative to cwd
# at import time (data/config.py's module-level CONFIG = Config.load()), so
# they must resolve against the real project root once, here, up front.
import src.states.bag_view
import src.states.battle_view
import src.states.dialog_view
import src.states.evolving_view
import src.states.menu_view
import src.states.pokedex_view
import src.states.pokemon_info_view
import src.states.pokemon_menu_view
import src.states.shop_view  # noqa: F401
from src.core.event_bus import global_bus
from src.core.events import (
    CloseViewEvent,
    OverlayViewEvent,
    SaveCompletedEvent,
    SaveGameRequestEvent,
    SwapViewEvent,
)
from src.core.game_director import GameDirector
from src.model.motion.player_motion import PlayerMotion


class DummyView(arcade.View):
    """Records the kwargs it was constructed with instead of doing real setup."""

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs
        # GameDirector's save-request handler reads this off the cached
        # Overworld and hands it straight to PlayerSerializer.serialize.
        self.player_state = PlayerMotion(
            map_name="littleroot_town", grid_x=0, grid_y=0, pixel_x=0.0, pixel_y=0.0
        )


@pytest.fixture
def director(arcade_window, save_manager, data_loader, monkeypatch):
    for target in (
        "src.states.overworld_view.OverworldView",
        "src.states.battle_view.BattleView",
        "src.states.evolving_view.EvolvingView",
        "src.states.menu_view.MenuView",
        "src.states.dialog_view.DialogView",
        "src.states.shop_view.ShopView",
        "src.states.pokedex_view.PokedexView",
        "src.states.bag_view.BagView",
        "src.states.pokemon_menu_view.PokemonMenuView",
        "src.states.pokemon_info_view.PokemonInfoView",
    ):
        monkeypatch.setattr(target, DummyView)

    return GameDirector(arcade_window)


def test_start_shows_overworld(director, arcade_window):
    director.start()
    assert isinstance(arcade_window.current_view, DummyView)
    assert director._view_cache["overworld"] is arcade_window.current_view


def test_overworld_is_singleton_across_swaps(director, arcade_window):
    director.start()
    first = arcade_window.current_view
    global_bus.publish(SwapViewEvent("overworld"))
    assert arcade_window.current_view is first


def test_swap_battle_threads_payload(director, arcade_window):
    director.start()
    global_bus.publish(
        SwapViewEvent(
            "battle",
            {"pokemon_name": "mudkip", "pokemon_data": object(), "pokemon_level": 5},
        )
    )
    view = arcade_window.current_view
    assert isinstance(view, DummyView)
    assert view.kwargs["foe_pokemon_name"] == "mudkip"
    assert view.kwargs["foe_level"] == 5
    assert view.kwargs["overworld_view"] is director._view_cache["overworld"]


def test_swap_battle_trainer_threads_payload(director, arcade_window):
    director.start()
    trainer_data = object()
    global_bus.publish(
        SwapViewEvent(
            "battle_trainer", {"trainer_data": trainer_data, "npc_id": "rival_1"}
        )
    )
    view = arcade_window.current_view
    assert view.kwargs["is_trainer"] is True
    assert view.kwargs["trainer_data"] is trainer_data
    assert view.kwargs["npc_id"] == "rival_1"


def test_swap_evolving_threads_payload(director, arcade_window):
    director.start()
    pokemon, evolved = object(), object()
    global_bus.publish(
        SwapViewEvent("evolving", {"pokemon": pokemon, "evolved_pokemon": evolved})
    )
    view = arcade_window.current_view
    assert view.kwargs["pokemon"] is pokemon
    assert view.kwargs["evolvedPokemon"] is evolved


@pytest.mark.parametrize(
    "target",
    ["menu", "dialog", "shop", "pokedex", "bag", "pokemon_menu", "pokemon_information"],
)
def test_overlay_targets_build_and_show(director, arcade_window, target):
    director.start()
    global_bus.publish(OverlayViewEvent(target))
    assert isinstance(arcade_window.current_view, DummyView)
    assert arcade_window.current_view is not director._view_cache["overworld"]


def test_overlay_defaults_previous_view_to_cached_overworld(director, arcade_window):
    director.start()
    global_bus.publish(OverlayViewEvent("bag"))
    view = arcade_window.current_view
    assert view.kwargs["previous_view"] is director._view_cache["overworld"]


def test_overlay_honors_explicit_previous_view(director, arcade_window):
    director.start()
    fake_previous = object()
    global_bus.publish(OverlayViewEvent("bag", {"previous_view": fake_previous}))
    view = arcade_window.current_view
    assert view.kwargs["previous_view"] is fake_previous


def test_forced_switch_reaches_pokemon_menu_view(director, arcade_window):
    director.start()
    global_bus.publish(OverlayViewEvent("pokemon_menu", {"forced_switch": True}))
    view = arcade_window.current_view
    assert view.kwargs["forced_switch"] is True


def test_pokemon_menu_defaults_forced_switch_false(director, arcade_window):
    director.start()
    global_bus.publish(OverlayViewEvent("pokemon_menu"))
    view = arcade_window.current_view
    assert view.kwargs["forced_switch"] is False


def test_close_view_returns_to_overworld(director, arcade_window):
    director.start()
    overworld = director._view_cache["overworld"]
    global_bus.publish(
        SwapViewEvent("evolving", {"pokemon": object(), "evolved_pokemon": object()})
    )
    assert arcade_window.current_view is not overworld

    global_bus.publish(CloseViewEvent())
    assert arcade_window.current_view is overworld


def test_save_request_succeeds_after_overworld_started(director, arcade_window):
    director.start()
    results = []
    global_bus.subscribe(SaveCompletedEvent, results.append)

    global_bus.publish(SaveGameRequestEvent())

    assert len(results) == 1
    assert results[0].success is True


def test_save_request_fails_before_overworld_exists(director):
    results = []
    global_bus.subscribe(SaveCompletedEvent, results.append)

    global_bus.publish(SaveGameRequestEvent())

    assert len(results) == 1
    assert results[0].success is False


# X3: _build_dialog dropped the `action` kwarg on the floor. overworld_view
# computed ("after_victory", "end") for a beaten trainer and published it, but
# DialogView never received it and fell back to npc.action_after_dialog =
# "fight" — so a beaten trainer re-fought forever, re-awarding prize money each
# time. Only the director sees this seam: both sides are individually correct.


def test_dialog_forwards_the_resolved_action(director, arcade_window):
    director.start()
    global_bus.publish(OverlayViewEvent("dialog", {"npc_id": "timmy", "action": "end"}))
    view = arcade_window.current_view
    assert view.kwargs["action"] == "end"


def test_dialog_action_defaults_to_none_when_unspecified(director, arcade_window):
    """None means 'no override' — DialogView then uses the NPC's own action."""
    director.start()
    global_bus.publish(OverlayViewEvent("dialog", {"npc_id": "timmy"}))
    view = arcade_window.current_view
    assert view.kwargs["action"] is None
