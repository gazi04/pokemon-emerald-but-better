"""Tests for OverworldView's non-drawing logic: NPC challenge eligibility,
dialog-state resolution, event-bus (un)subscription, and key handling.

`__init__` needs a real map/tmx and window, so these construct via `__new__`
and set only what each method reads — same pattern as
tests/unit/test_battle_view.py.
"""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import arcade

from src.core.event_bus import global_bus
from src.core.events import (
    BattleEncounterTriggeredEvent,
    NpcInteractEvent,
    NpcSpottedPlayerEvent,
)
from src.model.static.npc import NpcSpecies
from src.model.static.trainer import Trainer
from src.states.overworld_view import OverworldView

TRAINER_DATA = [
    {
        "name": "poochyena",
        "level": 5,
        "ability": "intimidate",
        "held_item": None,
        "moves": [{"name": "tackle", "pp": 25}],
    }
]


def make_view(data_loader, player_manager) -> Any:
    view: Any = OverworldView.__new__(OverworldView)
    view.data_loader = data_loader
    view.player_manager = player_manager
    view.npcs = []
    view.keys = set()
    view.cutscene = False
    return view


def add_npc_species(data_loader, npc_id, action_after_dialog, has_team=True):
    team = Trainer(TRAINER_DATA if has_team else [])
    species = NpcSpecies(
        name=npc_id, dialogs={}, action_after_dialog=action_after_dialog, team=team
    )
    data_loader.npc_dialog[npc_id] = species
    return species


# --- _can_challenge -----------------------------------------------------


def test_can_challenge_false_for_unknown_npc(data_loader, player_manager):
    view = make_view(data_loader, player_manager)

    assert view._can_challenge("ghost") is False


def test_can_challenge_false_when_not_a_fight_npc(data_loader, player_manager):
    add_npc_species(data_loader, "shopkeep", action_after_dialog="shop")
    view = make_view(data_loader, player_manager)

    assert view._can_challenge("shopkeep") is False


def test_can_challenge_false_when_team_is_empty(data_loader, player_manager):
    add_npc_species(data_loader, "rival", action_after_dialog="fight", has_team=False)
    view = make_view(data_loader, player_manager)

    assert view._can_challenge("rival") is False


def test_can_challenge_true_for_untested_battle_npc(data_loader, player_manager):
    add_npc_species(data_loader, "rival", action_after_dialog="fight")
    view = make_view(data_loader, player_manager)

    assert view._can_challenge("rival") is True


def test_can_challenge_false_once_already_fought(data_loader, player_manager):
    add_npc_species(data_loader, "rival", action_after_dialog="fight")
    player_manager.npc_manager.mark_fought("rival")
    view = make_view(data_loader, player_manager)

    assert view._can_challenge("rival") is False


# --- _resolve_dialog ------------------------------------------------------


def test_resolve_dialog_battle_npc_not_yet_beaten(data_loader, player_manager):
    npc = add_npc_species(data_loader, "rival", action_after_dialog="fight")
    view = make_view(data_loader, player_manager)

    assert view._resolve_dialog("rival", npc) == ("first_encounter", "fight")


def test_resolve_dialog_battle_npc_already_beaten(data_loader, player_manager):
    npc = add_npc_species(data_loader, "rival", action_after_dialog="fight")
    player_manager.npc_manager.mark_fought("rival")
    view = make_view(data_loader, player_manager)

    assert view._resolve_dialog("rival", npc) == ("after_victory", "end")


def test_resolve_dialog_non_battle_npc_uses_default(data_loader, player_manager):
    npc = add_npc_species(data_loader, "shopkeep", action_after_dialog="shop")
    view = make_view(data_loader, player_manager)

    assert view._resolve_dialog("shopkeep", npc) == ("default", "shop")


# --- subscribe/unsubscribe -------------------------------------------------


def test_subscribe_registers_all_three_handlers(data_loader, player_manager):
    view = make_view(data_loader, player_manager)

    view._subscribe()

    assert view._on_battle_triggered in global_bus._subscribers.get(
        BattleEncounterTriggeredEvent, []
    )
    assert view._on_npc_interaction in global_bus._subscribers.get(NpcInteractEvent, [])
    assert view._on_npc_spotted in global_bus._subscribers.get(
        NpcSpottedPlayerEvent, []
    )


def test_unsubscribe_removes_all_three_handlers(data_loader, player_manager):
    view = make_view(data_loader, player_manager)
    view.encounter_system = None
    view._subscribe()

    view._unsubscribe()

    assert view._on_battle_triggered not in global_bus._subscribers.get(
        BattleEncounterTriggeredEvent, []
    )
    assert view._on_npc_interaction not in global_bus._subscribers.get(
        NpcInteractEvent, []
    )


def test_unsubscribe_cleans_up_encounter_system(data_loader, player_manager):
    view = make_view(data_loader, player_manager)
    view.encounter_system = MagicMock()

    view._unsubscribe()

    view.encounter_system.cleanup.assert_called_once()


# --- _on_npc_spotted --------------------------------------------------------


def test_on_npc_spotted_freezes_input_and_faces_the_npc(data_loader, player_manager):
    view = make_view(data_loader, player_manager)
    view.keys = {arcade.key.UP}
    npc = SimpleNamespace(npc_id="rival", motion=SimpleNamespace(direction="down"))
    view.npcs = [npc]
    view.player_state = SimpleNamespace(direction="up")

    view._on_npc_spotted(NpcSpottedPlayerEvent(npc_id="rival"))

    assert view.cutscene is True
    assert view.keys == set()
    assert view.player_state.direction == "up"  # opposite of npc facing "down"


def test_on_npc_spotted_missing_npc_still_freezes(data_loader, player_manager):
    view = make_view(data_loader, player_manager)
    view.player_state = SimpleNamespace(direction="left")

    view._on_npc_spotted(NpcSpottedPlayerEvent(npc_id="ghost"))

    assert view.cutscene is True
    assert view.player_state.direction == "left"  # unchanged, npc not found


# --- on_key_press / on_key_release ------------------------------------------


def test_bag_key_clears_keys_and_opens_menu(data_loader, player_manager):
    view = make_view(data_loader, player_manager)
    view.keys = {arcade.key.UP}
    view.overlay = MagicMock()
    view.debug_collisions = False

    view.on_key_press(arcade.key.TAB, 0)

    assert view.keys == set()
    view.overlay.assert_called_once_with("menu")


def test_f1_toggles_debug_collisions(data_loader, player_manager):
    view = make_view(data_loader, player_manager)
    view.overlay = MagicMock()
    view.debug_collisions = False

    view.on_key_press(arcade.key.F1, 0)

    assert view.debug_collisions is True

    view.on_key_press(arcade.key.F1, 0)

    assert view.debug_collisions is False


def test_on_key_release_discards_key(data_loader, player_manager):
    view = make_view(data_loader, player_manager)
    view.keys = {arcade.key.UP, arcade.key.DOWN}

    view.on_key_release(arcade.key.UP, 0)

    assert view.keys == {arcade.key.DOWN}


# --- L8: first_encounter for non-battle NPCs --------------------------------
# _resolve_dialog returned "default" for anything that isn't a fight NPC, so the
# first_encounter lines authored for poke-mart-npc in npc_dialog.json never
# displayed. The state is chosen before mark_talked runs, so has_talked is still
# false on the very first interaction.


def add_talking_npc(data_loader, npc_id, action_after_dialog="shop", **dialogs):
    species = NpcSpecies(
        name=npc_id,
        dialogs=dialogs,
        action_after_dialog=action_after_dialog,
        team=Trainer([]),
    )
    data_loader.npc_dialog[npc_id] = species
    return species


def test_resolve_dialog_non_battle_npc_greets_on_the_first_visit(
    data_loader, player_manager
):
    npc = add_talking_npc(
        data_loader, "clerk", first_encounter=["Welcome!"], default=["Back again!"]
    )
    view = make_view(data_loader, player_manager)

    assert view._resolve_dialog("clerk", npc) == ("first_encounter", "shop")


def test_resolve_dialog_non_battle_npc_uses_default_once_talked_to(
    data_loader, player_manager
):
    npc = add_talking_npc(
        data_loader, "clerk", first_encounter=["Welcome!"], default=["Back again!"]
    )
    player_manager.npc_manager.mark_talked("clerk")
    view = make_view(data_loader, player_manager)

    assert view._resolve_dialog("clerk", npc) == ("default", "shop")


def test_resolve_dialog_skips_first_encounter_when_the_npc_has_none(
    data_loader, player_manager
):
    """Falling back to a state the NPC never authored would send get_dialog
    hunting through its fallback chain for nothing."""
    npc = add_talking_npc(data_loader, "clerk", default=["Hello."])
    view = make_view(data_loader, player_manager)

    assert view._resolve_dialog("clerk", npc) == ("default", "shop")
