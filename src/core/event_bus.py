from typing import Callable, Dict, List, Type, Any


class EventBus:
    def __init__(self):
        self._subscribers: Dict[Type, List[Callable]] = {}

    def subscribe(self, event_type: Type, listener: Callable[[Any], None]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(listener)

    def unsubscribe(self, event_type: Type, listener: Callable[[Any], None]):
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(listener)

    def publish(self, event: Any):
        event_type = type(event)
        for listener in self._subscribers.get(event_type, []):
            listener(event)


global_bus = EventBus()
