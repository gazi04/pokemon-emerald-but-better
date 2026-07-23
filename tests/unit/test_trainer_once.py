"""A trainer can be battled exactly once, win or lose. Starting the battle
spends the encounter (both the sight and interaction gates honour that), and
the battle must not drain the cached species roster."""

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
