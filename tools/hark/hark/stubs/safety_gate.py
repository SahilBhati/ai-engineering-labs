from __future__ import annotations

from collections.abc import Callable

from hark.events import (
    ConfirmationAnswered,
    ConfirmationAsked,
    ToolCallDecided,
    ToolCallRequested,
)
from hark.ports import EventBus, GateDecision, SpeechToText, TextToSpeech, ToolCall

YES = {"yes", "yeah", "yep"}


class StubSafetyGate:
    """Asks out loud when ``needs_yes`` says so; allows everything else.

    The real gate (lane D) owns the danger rules and the F6 checks on the
    answer; this stub only proves the flow and its events.
    """

    def __init__(
        self,
        bus: EventBus,
        tts: TextToSpeech,
        stt: SpeechToText,
        needs_yes: Callable[[ToolCall], bool] = lambda call: False,
    ) -> None:
        self._bus = bus
        self._tts = tts
        self._stt = stt
        self._needs_yes = needs_yes

    async def check(self, call: ToolCall) -> GateDecision:
        await self._bus.publish(
            ToolCallRequested(turn_id=call.turn_id, tool=call.tool, input=call.input)
        )
        if self._needs_yes(call):
            decision = await self._ask(call)
        else:
            decision = GateDecision(allowed=True, reason="no confirmation needed")
        await self._bus.publish(
            ToolCallDecided(
                turn_id=call.turn_id,
                tool=call.tool,
                allowed=decision.allowed,
                reason=decision.reason,
            )
        )
        return decision

    async def _ask(self, call: ToolCall) -> GateDecision:
        prompt = f"Allow {call.tool}? Say yes or no."
        await self._bus.publish(ConfirmationAsked(turn_id=call.turn_id, prompt=prompt))
        await self._tts.speak(prompt)
        answer = await self._stt.listen(timeout=5.0)
        heard = answer.text if answer else None
        confirmed = heard is not None and heard.strip(" .!").lower() in YES
        await self._bus.publish(
            ConfirmationAnswered(turn_id=call.turn_id, heard=heard, confirmed=confirmed)
        )
        if confirmed:
            return GateDecision(allowed=True, reason="user said yes")
        return GateDecision(allowed=False, reason="no answer" if heard is None else "user said no")
