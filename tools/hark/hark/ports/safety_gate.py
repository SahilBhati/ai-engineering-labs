"""Safety gate port: the policy decision point for tool calls (R5, D6).

The brain's pre-tool hook (the enforcement point) sends every tool call
here and blocks unless the answer is a clear allow. Deleting, pushing,
publishing or sending a message needs a spoken yes; silence or "no" denies.

Implementations publish, for each call: ``ToolCallRequested``, then
``ConfirmationAsked`` and ``ConfirmationAnswered`` if they asked, then
``ToolCallDecided``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ToolCall:
    turn_id: str
    tool: str  # e.g. "Bash"
    input: Mapping[str, Any]  # e.g. {"command": "git push"}


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str


@runtime_checkable
class SafetyGate(Protocol):
    async def check(self, call: ToolCall) -> GateDecision: ...
