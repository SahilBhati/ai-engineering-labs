"""Wake word port: start a turn on a configurable phrase (R1, D2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Wake:
    phrase: str
    score: float


@runtime_checkable
class WakeWord(Protocol):
    """Strategy: the detector and its model file are swappable."""

    async def wait(self) -> Wake:
        """Return when the wake phrase is heard."""
        ...
