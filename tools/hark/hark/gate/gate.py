"""``HarkSafetyGate``: the policy decision point (R5, D6).

Clearly safe calls are decided at once with no voice. Everything else is
asked out loud and needs a clear spoken yes; any doubt or failure denies.
Publishes the same events, in the same order, as the stub.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from hark.events import (
    ConfirmationAnswered,
    ConfirmationAsked,
    ToolCallDecided,
    ToolCallRequested,
)
from hark.gate.classify import UNCHECKED, Kind, Verdict, classify
from hark.gate.confirm import Confirmation, Confirmer
from hark.ports import EventBus, GateDecision, SpeechToText, TextToSpeech, ToolCall

logger = logging.getLogger(__name__)

type Classifier = Callable[[ToolCall], Verdict]

# The block reason is what Claude repeats to the user, so each is a plain sentence.
DENIALS = {
    "no": "Denied: you said no to a request to {}.",
    "silence": "Denied: there was no spoken yes to a request to {}.",
    "unclear": "Denied: I did not hear a clear yes to a request to {}.",
}


class HarkSafetyGate:
    def __init__(
        self,
        bus: EventBus,
        tts: TextToSpeech,
        stt: SpeechToText,
        classifier: Classifier = classify,
        confirmer: Confirmer | None = None,
    ) -> None:
        self._bus = bus
        self._tts = tts
        self._classify = classifier
        self._confirmer = confirmer or Confirmer(tts, stt)

    async def check(self, call: ToolCall) -> GateDecision:
        await self._bus.publish(
            ToolCallRequested(turn_id=call.turn_id, tool=call.tool, input=call.input)
        )
        decision = GateDecision(False, "Denied: the safety check did not finish.")
        try:
            decision = await self._decide(call)
        except asyncio.CancelledError:
            decision = GateDecision(False, "Denied: the request went away before you answered.")
            raise
        except Exception:
            logger.exception("safety gate failed; denying")
            decision = GateDecision(False, "Denied: the safety check failed.")
        finally:
            await self._bus.publish(
                ToolCallDecided(
                    turn_id=call.turn_id,
                    tool=call.tool,
                    allowed=decision.allowed,
                    reason=decision.reason,
                )
            )
        return decision

    def _verdict(self, call: ToolCall) -> Verdict:
        try:
            return self._classify(call)
        except Exception:  # noqa: BLE001 — a broken classifier means ask
            logger.exception("classifier failed; asking")
            return Verdict(Kind.ASK, UNCHECKED)

    async def _decide(self, call: ToolCall) -> GateDecision:
        verdict = self._verdict(call)
        if verdict.allowed:
            return GateDecision(True, verdict.reason)
        prompt = f"Allow: {verdict.reason}? Say yes or no."
        await self._bus.publish(ConfirmationAsked(turn_id=call.turn_id, prompt=prompt))
        await self._tts.speak(prompt)
        answer: Confirmation = await self._confirmer.confirm()
        await self._bus.publish(
            ConfirmationAnswered(turn_id=call.turn_id, heard=answer.heard, confirmed=answer.confirmed)
        )
        if answer.confirmed:
            return GateDecision(True, "you said yes")
        return GateDecision(False, DENIALS[answer.outcome].format(verdict.reason))

