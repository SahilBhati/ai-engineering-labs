"""Event bus port: publish turn events to subscribers (D8, pattern: Observer)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

from hark.events import Event

type Handler = Callable[[Event], Awaitable[None]]


@runtime_checkable
class EventBus(Protocol):
    async def publish(self, event: Event) -> None:
        """Deliver to every subscriber. A failing subscriber must not break the turn."""
        ...

    def subscribe(self, handler: Handler) -> None: ...
