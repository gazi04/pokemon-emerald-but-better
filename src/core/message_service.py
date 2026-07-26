from __future__ import annotations
from typing import Protocol
from collections.abc import Callable

from src.core.events import TextMessageEvent
from src.core.logger import get_logger

log = get_logger(__name__)


class MessageBox(Protocol):
    """Structural contract the service needs from a text box. Keeps `core`
    independent of `ui` — TypewriterMessageBox satisfies this implicitly."""

    is_processing: bool

    def queue_message(self, message: str) -> None: ...
    def set_on_complete(self, callback: Callable) -> None: ...
    def clear(self) -> None: ...


class MessageService:
    """Routes a message to the currently-active text box. Owned by GameDirector;
    the visible box-owning view registers its box via set_box()."""

    def __init__(self) -> None:
        self._box: MessageBox | None = None

    def set_box(self, box: MessageBox | None) -> None:
        self._box = box

    def show(self, messages: str | list[str], callback: Callable | None = None) -> None:
        if self._box is None:
            log.warning("show() with no active box; dropped: %s", messages)
            return
        if isinstance(messages, str):
            messages = [messages]
        for m in messages:
            self._box.queue_message(m)
        if callback:
            self._box.set_on_complete(callback)

    def clear(self) -> None:
        if self._box:
            self._box.clear()

    def is_idle(self) -> bool:
        return self._box is None or not self._box.is_processing

    def on_message_event(self, event: TextMessageEvent) -> None:
        """Adapter for global_bus — lets systems show text with no view ref."""
        self.show(event.message)
