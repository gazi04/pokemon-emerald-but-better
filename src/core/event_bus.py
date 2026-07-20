from typing import Callable, Dict, List, Type, Any

from src.core.logger import get_logger

log = get_logger(__name__)


class EventBus:
    def __init__(self):
        self._subscribers: Dict[Type, List[Callable]] = {}

    def subscribe(self, event_type: Type, listener: Callable[[Any], None]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        # Prevent duplicate subscriptions
        if listener not in self._subscribers[event_type]:
            self._subscribers[event_type].append(listener)

    def unsubscribe(self, event_type: Type, listener: Callable[[Any], None]):
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(listener)
            except ValueError:
                # Listener was not subscribed, silently ignore
                pass

    def publish(self, event: Any):
        event_type = type(event)
        for listener in list(self._subscribers.get(event_type, [])):
            try:
                listener(event)
            except Exception:
                log.exception("Listener failed for %s", event_type.__name__)


global_bus = EventBus()
