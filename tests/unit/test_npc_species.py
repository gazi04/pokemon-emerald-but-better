"""Tests for NpcSpecies.get_dialog's fallback chain and has_state."""

from src.model.static.npc import NpcSpecies
from src.model.static.trainer import Trainer


def make_species(dialogs):
    return NpcSpecies(
        name="elm", dialogs=dialogs, action_after_dialog="talk", team=Trainer([])
    )


def test_exact_state_match_wins():
    species = make_species({"default": ["default line"], "after_fight": ["fight line"]})

    assert species.get_dialog("after_fight") == ["fight line"]


def test_falls_back_to_default_when_state_missing():
    species = make_species({"default": ["default line"], "other": ["other line"]})

    assert species.get_dialog("missing_state") == ["default line"]


def test_falls_back_to_first_encounter_when_no_default():
    species = make_species({"first_encounter": ["hi!"], "other": ["other line"]})

    assert species.get_dialog("missing_state") == ["hi!"]


def test_falls_back_to_any_dialog_value_when_no_default_or_first_encounter():
    species = make_species({"custom_state": ["only line"]})

    assert species.get_dialog("missing_state") == ["only line"]


def test_placeholder_when_no_dialogs_at_all():
    species = make_species({})

    assert species.get_dialog("anything") == ["..."]


def test_has_state_true_for_known_state():
    species = make_species({"default": ["x"]})

    assert species.has_state("default") is True


def test_has_state_false_for_unknown_state():
    species = make_species({"default": ["x"]})

    assert species.has_state("nope") is False
