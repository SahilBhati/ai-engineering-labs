"""``Notifier``: show an answer's detail as a Mac notification (F7).

The spoken reply stays short; the detail (paths, diffs, lists) goes to the
screen. Only ``Answered`` events that carry a detail notify.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from hark.events import Answered, Event

logger = logging.getLogger(__name__)

type Runner = Callable[[list[str]], Awaitable[None]]


async def _osascript(argv: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
    )
    _, err = await proc.communicate()
    if proc.returncode:
        logger.error("notification failed: %s", err.decode().strip())


# Reply text arrives as argv items to this fixed script, never parsed as AppleScript.
_SCRIPT = (
    "on run argv\n"
    "display notification (item 2 of argv) with title (item 1 of argv)\n"
    "end run"
)


class Notifier:
    def __init__(self, title: str = "Hark", run: Runner = _osascript, max_chars: int = 400) -> None:
        self._title = title
        self._run = run
        self._max = max_chars

    async def handle(self, event: Event) -> None:
        if not isinstance(event, Answered) or not event.detail:
            return
        body = event.detail if len(event.detail) <= self._max else event.detail[: self._max - 1] + "…"
        await self._run(["osascript", "-e", _SCRIPT, self._title, body])
