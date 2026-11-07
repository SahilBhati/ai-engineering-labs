from __future__ import annotations

from hark.events import Event
from hark.ports import Handler


class InMemoryEventBus:
    """Keeps every event in order and forwards it to subscribers."""

    def __init__(self) -> None:
        self.events: list[Event] = []
        self._handlers: list[Handler] = []

    async def publish(self, event: Event) -> None:
        self.events.append(event)
        for handler in self._handlers:
            await handler(event)

    def subscribe(self, handler: Handler) -> None:
        self._handlers.append(handler)
