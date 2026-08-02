"""Tests for DialogManager: JSON loading + state-based dialog selection."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.systems.dialog_manager import DialogManager

DIALOGS = {
    "elm": {
        "first_encounter": ["Hi there!"],
        "after_fight": ["Good match."],
        "after_defeat": ["You beat me..."],
        "revisit": ["Hey again."],
        "default": ["..."],
    },
    "no_default_npc": {
        "custom": ["Only this line."],
    },
}


def make_npc_manager(defeated=False, has_fought=False, has_talked=False):
    manager = MagicMock()
    manager.get_state.return_value = SimpleNamespace(
        defeated=defeated, has_fought=has_fought, has_talked=has_talked
    )
    return manager


@pytest.fixture
def dialog_path(tmp_path):
    path = tmp_path / "npc_dialog.json"
    path.write_text(json.dumps(DIALOGS))
    return str(path)


def test_missing_file_falls_back_to_empty_dialogs(tmp_path):
    manager = DialogManager(
        make_npc_manager(), dialog_path=str(tmp_path / "missing.json")
    )

    assert manager.dialogs == {}
    assert manager.get_dialog_lines("elm") == ["..."]
    assert manager.get_dialog_type("elm") == "none"
    assert manager.has_battle_dialog("elm") is False


def test_unknown_npc_returns_placeholder(dialog_path):
    manager = DialogManager(make_npc_manager(), dialog_path=dialog_path)

    assert manager.get_dialog_lines("ghost") == ["..."]
    assert manager.get_dialog_type("ghost") == "none"
    assert manager.has_battle_dialog("ghost") is False


def test_defeated_takes_priority(dialog_path):
    manager = DialogManager(
        make_npc_manager(defeated=True, has_fought=True, has_talked=True),
        dialog_path=dialog_path,
    )

    assert manager.get_dialog_lines("elm") == ["You beat me..."]
    assert manager.get_dialog_type("elm") == "after_defeat"


def test_has_fought_beats_revisit(dialog_path):
    manager = DialogManager(
        make_npc_manager(defeated=False, has_fought=True, has_talked=True),
        dialog_path=dialog_path,
    )

    assert manager.get_dialog_lines("elm") == ["Good match."]
    assert manager.get_dialog_type("elm") == "after_fight"


def test_has_talked_returns_revisit(dialog_path):
    manager = DialogManager(make_npc_manager(has_talked=True), dialog_path=dialog_path)

    assert manager.get_dialog_lines("elm") == ["Hey again."]
    assert manager.get_dialog_type("elm") == "revisit"


def test_first_encounter_when_never_talked(dialog_path):
    manager = DialogManager(make_npc_manager(), dialog_path=dialog_path)

    assert manager.get_dialog_lines("elm") == ["Hi there!"]
    assert manager.get_dialog_type("elm") == "first_encounter"


def test_falls_back_to_default_when_no_first_encounter_key(dialog_path):
    """not-yet-talked but the npc has no 'first_encounter' key: get_dialog_lines
    falls through to 'default'. get_dialog_type only reads the state flags (not
    dict keys), so it still reports "first_encounter" for the same npc/state —
    the "default" branch in get_dialog_type is unreachable for a bool state."""
    manager = DialogManager(make_npc_manager(), dialog_path=dialog_path)
    manager.dialogs["barren"] = {"default": ["Only default."]}

    assert manager.get_dialog_lines("barren") == ["Only default."]
    assert manager.get_dialog_type("barren") == "first_encounter"


def test_last_resort_returns_first_available_dialog(dialog_path):
    manager = DialogManager(make_npc_manager(), dialog_path=dialog_path)

    assert manager.get_dialog_lines("no_default_npc") == ["Only this line."]


def test_has_battle_dialog_true_for_fight_or_defeat_keys(dialog_path):
    manager = DialogManager(make_npc_manager(), dialog_path=dialog_path)

    assert manager.has_battle_dialog("elm") is True
    assert manager.has_battle_dialog("no_default_npc") is False
