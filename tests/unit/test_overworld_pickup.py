"""Picking a ground item up puts it in the bag exactly once, and it stays gone."""

import pytest

from src.core.player_serializer import PlayerSerializer

KEY = "littleroot_town:potion_start"


@pytest.fixture
def manager(player_manager):
    return player_manager


def count_of(manager, item_id):
    stack = manager.player.items.get(item_id)
    return stack.count if stack else 0


def test_collecting_adds_the_item_to_the_bag(manager):
    before = count_of(manager, "potion")

    assert manager.collect_overworld_item(KEY, "potion") is True
    assert count_of(manager, "potion") == before + 1


def test_collecting_records_the_key(manager):
    manager.collect_overworld_item(KEY, "potion")
    assert KEY in manager.collected_item_keys()


def test_the_same_item_cannot_be_collected_twice(manager):
    manager.collect_overworld_item(KEY, "potion")
    before = count_of(manager, "potion")

    assert manager.collect_overworld_item(KEY, "potion") is False
    assert count_of(manager, "potion") == before  # no duplicate


def test_different_items_are_tracked_separately(manager):
    manager.collect_overworld_item(KEY, "potion")
    assert manager.collect_overworld_item("oldale_town:potion_2", "potion") is True
    assert len(manager.collected_item_keys()) == 2


def test_collected_keys_survive_a_save_reload(manager):
    manager.collect_overworld_item(KEY, "potion")

    restored = PlayerSerializer.deserialize(PlayerSerializer.serialize(manager.player))
    assert KEY in restored.collected_items


def test_a_fresh_save_has_nothing_collected(manager):
    assert manager.collected_item_keys() == set()
