"""Brain port: the open-ended path, Claude Code in v1 (R2, R3, D5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class BrainRequest:
    turn_id: str
    text: str


@dataclass(frozen=True)
class BrainReply:
    spoken: str  # short, said aloud (F4, F7)
    detail: str | None = None  # long form, shown on screen


@runtime_checkable
class Brain(Protocol):
    """Adapter over the brain process.

    The adapter owns its process: start, restart on crash, session rollover.
    Tool calls the brain makes go through the safety gate before they run.
    """

    async def ask(self, request: BrainRequest) -> BrainReply: ...
