"""Router port: fast local action, or hand the turn to the brain (D4).

A wrong fast guess runs the wrong action; a wrong brain guess only costs
time. So no match, or a weak match, must return ``ToBrain``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class FastAction:
    action: str  # name in the action registry
    score: float
    args: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ToBrain:
    score: float = 0.0  # best fast-path score seen; logged for the miss rate


type Route = FastAction | ToBrain


@runtime_checkable
class Router(Protocol):
    """Strategy: rules today, a local model later if the miss rate says so."""

    async def route(self, text: str) -> Route: ...
