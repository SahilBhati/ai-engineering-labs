"""Turn events, published on the event bus (pattern: Observer).

Every event carries the turn it belongs to and a monotonic timestamp
(``time.monotonic()`` seconds). One clock for every stage is what makes
per-stage timings and "time from end of speech" (R6) comparable.

Subscribers in v1: the turn log and notifications. A future app is just
another subscriber, so events hold data only — no UI logic.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any, Literal


def now() -> float:
    """The one clock every event and stage timing uses."""
    return time.monotonic()


@dataclass(frozen=True, kw_only=True)
class Event:
    turn_id: str
    ts: float = field(default_factory=now)

    def to_dict(self) -> dict[str, Any]:
        """Plain dict with a ``type`` key, ready for a JSON-lines stream."""
        return {"type": type(self).__name__, **asdict(self)}


@dataclass(frozen=True, kw_only=True)
class TurnStarted(Event):
    wake_phrase: str


@dataclass(frozen=True, kw_only=True)
class Transcribed(Event):
    text: str
    speech_ended_at: float  # same clock as ``ts``; R6 measures from here


@dataclass(frozen=True, kw_only=True)
class Routed(Event):
    route: Literal["fast", "brain"]
    action: str | None  # set for the fast path
    score: float  # best match score; logged for the D4 miss rate


@dataclass(frozen=True, kw_only=True)
class ToolCallRequested(Event):
    tool: str
    input: Mapping[str, Any]


@dataclass(frozen=True, kw_only=True)
class ConfirmationAsked(Event):
    prompt: str


@dataclass(frozen=True, kw_only=True)
class ConfirmationAnswered(Event):
    heard: str | None  # None means silence
    confirmed: bool


@dataclass(frozen=True, kw_only=True)
class ToolCallDecided(Event):
    tool: str
    allowed: bool
    reason: str


@dataclass(frozen=True, kw_only=True)
class Answered(Event):
    spoken: str
    detail: str | None = None  # goes to the screen, not the speaker (F7)


@dataclass(frozen=True, kw_only=True)
class StageTimed(Event):
    stage: str
    started: float
    ended: float

    @property
    def duration(self) -> float:
        return self.ended - self.started


@dataclass(frozen=True, kw_only=True)
class TurnEnded(Event):
    """Always the last event of a turn."""

    outcome: Literal["answered", "no_speech", "error"]
