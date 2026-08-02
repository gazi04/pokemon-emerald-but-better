"""Tests for MessageService: routing text to whatever box is registered."""

from unittest.mock import MagicMock

from src.core.events import TextMessageEvent
from src.core.message_service import MessageService


def make_box(is_processing=False):
    box = MagicMock()
    box.is_processing = is_processing
    return box


def test_show_with_no_box_is_a_noop():
    service = MessageService()

    service.show("hello")  # must not raise


def test_show_coerces_a_single_string_to_one_message():
    service = MessageService()
    box = make_box()
    service.set_box(box)

    service.show("hello")

    box.queue_message.assert_called_once_with("hello")


def test_show_queues_every_message_in_a_list():
    service = MessageService()
    box = make_box()
    service.set_box(box)

    service.show(["one", "two", "three"])

    assert box.queue_message.call_count == 3
    box.queue_message.assert_any_call("one")
    box.queue_message.assert_any_call("two")
    box.queue_message.assert_any_call("three")


def test_show_registers_callback_when_given():
    service = MessageService()
    box = make_box()
    service.set_box(box)
    callback = MagicMock()

    service.show("hi", callback=callback)

    box.set_on_complete.assert_called_once_with(callback)


def test_show_without_callback_does_not_touch_on_complete():
    service = MessageService()
    box = make_box()
    service.set_box(box)

    service.show("hi")

    box.set_on_complete.assert_not_called()


def test_clear_with_no_box_is_a_noop():
    service = MessageService()

    service.clear()  # must not raise


def test_clear_delegates_to_the_box():
    service = MessageService()
    box = make_box()
    service.set_box(box)

    service.clear()

    box.clear.assert_called_once()


def test_is_idle_true_with_no_box():
    service = MessageService()

    assert service.is_idle() is True


def test_is_idle_true_when_box_not_processing():
    service = MessageService()
    service.set_box(make_box(is_processing=False))

    assert service.is_idle() is True


def test_is_idle_false_when_box_processing():
    service = MessageService()
    service.set_box(make_box(is_processing=True))

    assert service.is_idle() is False


def test_on_message_event_delegates_to_show():
    service = MessageService()
    box = make_box()
    service.set_box(box)

    service.on_message_event(TextMessageEvent(message="bark"))

    box.queue_message.assert_called_once_with("bark")


def test_set_box_none_makes_service_idle_again():
    service = MessageService()
    service.set_box(make_box(is_processing=True))
    assert service.is_idle() is False

    service.set_box(None)

    assert service.is_idle() is True
