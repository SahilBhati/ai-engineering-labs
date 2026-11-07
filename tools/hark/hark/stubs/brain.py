from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from hark.ports import BrainReply, BrainRequest, SafetyGate, ToolCall


class StubBrain:
    """Makes scripted tool calls through the gate, as the pre-tool hook would,
    then replies. Any denied call turns the reply into a cancellation.
    """

    def __init__(
        self,
        gate: SafetyGate,
        reply: BrainReply,
        tool_calls: Sequence[tuple[str, Mapping[str, Any]]] = (),
    ) -> None:
        self._gate = gate
        self._reply = reply
        self._tool_calls = tool_calls
        self.requests: list[BrainRequest] = []

    async def ask(self, request: BrainRequest) -> BrainReply:
        self.requests.append(request)
        for tool, tool_input in self._tool_calls:
            decision = await self._gate.check(ToolCall(request.turn_id, tool, tool_input))
            if not decision.allowed:
                return BrainReply(spoken="Cancelled.", detail=decision.reason)
        return self._reply
