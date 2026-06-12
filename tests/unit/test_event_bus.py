from dataclasses import dataclass

import pytest

from src.core.event_bus import EventBus


@dataclass
class FooEvent:
    value: int


@dataclass
class BarEvent:
    text: str


def test_subscribe_and_publish_calls_listener(event_bus):
    received = []
    event_bus.subscribe(FooEvent, received.append)
    event_bus.publish(FooEvent(value=42))
    assert len(received) == 1
    assert received[0].value == 42


def test_listener_receives_correct_instance(event_bus):
    received = []
    event_bus.subscribe(FooEvent, received.append)
    event = FooEvent(value=7)
    event_bus.publish(event)
    assert received[0] is event


def test_multiple_listeners_all_called(event_bus):
    calls = []
    event_bus.subscribe(FooEvent, lambda e: calls.append("a"))
    event_bus.subscribe(FooEvent, lambda e: calls.append("b"))
    event_bus.publish(FooEvent(value=1))
    assert calls == ["a", "b"]


def test_unsubscribe_stops_delivery(event_bus):
    received = []
    listener = received.append
    event_bus.subscribe(FooEvent, listener)
    event_bus.unsubscribe(FooEvent, listener)
    event_bus.publish(FooEvent(value=1))
    assert received == []


def test_unsubscribe_unknown_listener_raises(event_bus):
    # Subscribe one listener to ensure the event_type key exists, then try
    # to remove a different listener that was never registered.
    event_bus.subscribe(FooEvent, lambda e: None)
    with pytest.raises(ValueError):
        event_bus.unsubscribe(FooEvent, lambda e: None)


def test_publish_with_no_subscribers_is_safe(event_bus):
    event_bus.publish(FooEvent(value=0))  # no error


def test_different_event_types_only_call_matching_listener(event_bus):
    foo_calls = []
    bar_calls = []
    event_bus.subscribe(FooEvent, foo_calls.append)
    event_bus.subscribe(BarEvent, bar_calls.append)

    event_bus.publish(FooEvent(value=1))
    assert len(foo_calls) == 1
    assert len(bar_calls) == 0

    event_bus.publish(BarEvent(text="hi"))
    assert len(foo_calls) == 1
    assert len(bar_calls) == 1


def test_publish_multiple_times_calls_listener_each_time(event_bus):
    calls = []
    event_bus.subscribe(FooEvent, calls.append)
    event_bus.publish(FooEvent(value=1))
    event_bus.publish(FooEvent(value=2))
    assert len(calls) == 2
