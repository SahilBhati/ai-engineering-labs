"""``AsyncEventBus``: fan events out to subscribers without ever waiting on one.

Pattern: Observer. Each subscriber gets its own queue and worker task, so a
slow or hung subscriber delays only itself, and ``publish`` returns at once.
A handler that raises is logged and skipped; one that exceeds
``handler_timeout`` is abandoned for that event. Events reach each
subscriber in publish order.
"""

from __future__ import annotations

import asyncio
import logging

from hark.events import Event
from hark.ports import Handler

logger = logging.getLogger(__name__)


class _Subscriber:
    def __init__(self, handler: Handler, timeout: float, max_queue: int) -> None:
        self.handler = handler
        self.timeout = timeout
        self.queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=max_queue)
        self.task: asyncio.Task[None] | None = None

    async def run(self) -> None:
        while True:
            event = await self.queue.get()
            try:
                await asyncio.wait_for(self.handler(event), self.timeout)
            except TimeoutError:
                logger.error("subscriber %r timed out on %s", self.handler, type(event).__name__)
            except Exception:
                logger.exception("subscriber %r failed on %s", self.handler, type(event).__name__)
            finally:
                self.queue.task_done()


class AsyncEventBus:
    def __init__(self, handler_timeout: float = 5.0, max_queue: int = 1000) -> None:
        self._timeout = handler_timeout
        self._max_queue = max_queue
        self._subscribers: list[_Subscriber] = []

    def subscribe(self, handler: Handler) -> None:
        self._subscribers.append(_Subscriber(handler, self._timeout, self._max_queue))

    async def publish(self, event: Event) -> None:
        for sub in self._subscribers:
            if sub.task is None:  # workers start lazily, inside the running loop
                sub.task = asyncio.create_task(sub.run())
            try:
                sub.queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.error("subscriber %r is %d events behind; dropped %s",
                             sub.handler, self._max_queue, type(event).__name__)

    async def drain(self, timeout: float | None = None) -> None:
        """Wait until every subscriber has handled everything published so far."""
        await asyncio.wait_for(
            asyncio.gather(*(s.queue.join() for s in self._subscribers)), timeout
        )

    async def close(self) -> None:
        """Deliver what is queued, then stop the workers."""
        try:
            await self.drain(self._timeout * 2)
        except TimeoutError:
            logger.error("event bus closed with undelivered events")
        for sub in self._subscribers:
            if sub.task is not None:
                sub.task.cancel()
        await asyncio.gather(
            *(s.task for s in self._subscribers if s.task), return_exceptions=True
        )
        for sub in self._subscribers:
            sub.task = None
