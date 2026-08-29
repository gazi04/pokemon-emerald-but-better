"""A trainer can be battled exactly once, win or lose. Starting the battle
spends the encounter (both the sight and interaction gates honour that), and
the battle must not drain the cached species roster."""

from types import SimpleNamespace
from typing import Any

from src.model.static.trainer import Trainer
from src.systems.npc_manager import NPCManager

ROSTER = [
    {
        "name": "zigzagoon",
        "level": 5,
        "ability": "pickup",
        "held_item": None,
        "moves": [{"name": "tackle", "pp": 25}],
    }
]


# --- defeated state is the once-only switch ---------------------------------


def test_fresh_trainer_can_be_fought():
    assert NPCManager().can_fight("rival")


def test_winning_uses_up_the_encounter():
    manager = NPCManager()
    manager.mark_fought("rival")
    manager.mark_defeated("rival")
    assert not manager.can_fight("rival")


def test_losing_also_uses_up_the_encounter():
    """Whiting out must not hand back a rematch — the battle started, so it
    counts even though `defeated` was never set."""
    manager = NPCManager()
    manager.mark_fought("rival")  # battle began, player then whited out

    assert not manager.get_state("rival").defeated
    assert not manager.can_fight("rival")


def test_spent_encounter_survives_save_reload():
    manager = NPCManager()
    manager.mark_fought("rival")

    reloaded = NPCManager()
    reloaded.load_from_dict(manager.save_to_dict())
    assert not reloaded.can_fight("rival")


def test_other_npcs_are_unaffected():
    manager = NPCManager()
    manager.mark_fought("rival")
    assert manager.can_fight("someone_else")


# --- battle must not drain the cached roster --------------------------------


def test_clone_does_not_drain_original():
    team = Trainer(ROSTER)
    battle_copy = team.clone()

    # A battle pops the copy's party as Pokémon faint.
    battle_copy.party.pop(0)

    assert battle_copy.party == []  # copy consumed
    assert len(team.party) == 1  # template intact for next encounter


def test_clone_shares_no_party_list_identity():
    team = Trainer(ROSTER)
    assert team.clone().party is not team.party


# --- prize money -------------------------------------------------------------


TWO_MON_ROSTER = [
    *ROSTER,
    {
        "name": "poochyena",
        "level": 7,
        "ability": "run_away",
        "held_item": None,
        "moves": [{"name": "tackle", "pp": 25}],
    },
]


def test_prize_money_sums_every_party_level_once():
    """Regression: the old inline calculation in BattleView added the lead's
    level a second time, because it summed `party` before popping the lead."""
    assert Trainer(TWO_MON_ROSTER).prize_money() == (5 + 7) * 10


def test_prize_money_single_pokemon():
    assert Trainer(ROSTER).prize_money() == 5 * 10


def test_prize_money_empty_party():
    assert Trainer([]).prize_money() == 0


def test_prize_money_must_be_read_before_the_party_drains():
    """Documents the ordering constraint BattleView relies on."""
    team = Trainer(TWO_MON_ROSTER)
    full = team.prize_money()
    team.party.pop(0)
    assert team.prize_money() < full


# --- the interaction gate ---------------------------------------------------
# can_fight() gated NPC-initiated spotting (overworld_view._can_challenge) but
# nothing gated walking up and talking to a beaten trainer. DialogView now
# honours the action the overworld resolved, and refuses the fight outright if
# the encounter is already spent.


def _dialog_view(npc_id="rival", npc_manager=None) -> Any:
    from unittest.mock import MagicMock

    from src.states.dialog_view import DialogView

    view: Any = DialogView.__new__(DialogView)
    view.npc_id = npc_id
    view.npc = MagicMock()
    view.player_manager = MagicMock()
    view.player_manager.npc_manager = npc_manager or NPCManager()
    view.swap = MagicMock()
    view.close = MagicMock()
    return view


def test_action_fight_starts_the_battle_for_a_fresh_trainer():
    view = _dialog_view()

    view._action_fight()

    view.swap.assert_called_once()


def test_action_fight_refuses_once_the_encounter_is_spent():
    manager = NPCManager()
    manager.mark_fought("rival")
    manager.mark_defeated("rival")
    view = _dialog_view(npc_manager=manager)

    view._action_fight()

    view.swap.assert_not_called()


def test_action_override_wins_over_the_npcs_own_action():
    """A beaten trainer resolves to 'end', which must beat the NPC template's
    'fight' — the value the director used to drop."""
    from src.states.dialog_view import DialogView

    npc = SimpleNamespace(action_after_dialog="fight")

    assert DialogView._resolve_action(npc, "end") == "end"
    assert DialogView._resolve_action(npc, None) == "fight"
