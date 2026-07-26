import contextlib
from typing import Any
from collections.abc import Callable

from src.core.logger import get_logger

log = get_logger(__name__)


class EventBus:
    def __init__(self):
        self._subscribers: dict[type, list[Callable]] = {}

    def subscribe(self, event_type: type, listener: Callable[[Any], None]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        # Prevent duplicate subscriptions
        if listener not in self._subscribers[event_type]:
            self._subscribers[event_type].append(listener)

    def unsubscribe(self, event_type: type, listener: Callable[[Any], None]):
        if event_type in self._subscribers:
            # Listener was not subscribed, silently ignore
            with contextlib.suppress(ValueError):
                self._subscribers[event_type].remove(listener)

    def publish(self, event: Any):
        event_type = type(event)
        for listener in list(self._subscribers.get(event_type, [])):
            try:
                listener(event)
            except Exception:
                log.exception("Listener failed for %s", event_type.__name__)


global_bus = EventBus()
