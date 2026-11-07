"""Run one turn through the ports and time each stage (R6).

Fast path:  wake → listen → route → action → speak
Brain path: wake → listen → route → "on it" → brain → speak

Event sequence per turn: ``TurnStarted``, ``Transcribed``, ``Routed``,
then ``Answered`` and ``TurnEnded``, with a ``StageTimed`` as each stage
ends. Gate events appear inside the brain stage. A turn with no speech goes
straight from ``TurnStarted`` to ``TurnEnded(outcome="no_speech")``.

This is the minimal wiring the ports are proven against; the integration
step grows it into the app.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from hark.events import (
    Answered,
    Routed,
    StageTimed,
    Transcribed,
    TurnEnded,
    TurnStarted,
    now,
)
from hark.ports import (
    ActionRegistry,
    Brain,
    BrainReply,
    BrainRequest,
    EventBus,
    FastAction,
    Router,
    SpeechToText,
    TextToSpeech,
    WakeWord,
)

ACK = "On it."


@dataclass
class TurnRunner:
    wake: WakeWord
    stt: SpeechToText
    router: Router
    actions: ActionRegistry
    brain: Brain
    tts: TextToSpeech
    bus: EventBus

    async def run_once(self) -> str:
        """Wait for the wake phrase, run one turn, return its turn id."""
        wake = await self.wake.wait()
        turn_id = uuid.uuid4().hex
        await self.bus.publish(TurnStarted(turn_id=turn_id, wake_phrase=wake.phrase))
        outcome = "error"
        try:
            outcome = await self._run(turn_id)
        finally:
            await self.bus.publish(TurnEnded(turn_id=turn_id, outcome=outcome))
        return turn_id

    async def _run(self, turn_id: str) -> str:
        async with self._stage(turn_id, "listen"):
            transcript = await self.stt.listen()
        if transcript is None:
            return "no_speech"
        await self.bus.publish(
            Transcribed(
                turn_id=turn_id,
                text=transcript.text,
                speech_ended_at=transcript.speech_ended_at,
            )
        )

        async with self._stage(turn_id, "route"):
            route = await self.router.route(transcript.text)
        fast = isinstance(route, FastAction)
        await self.bus.publish(
            Routed(
                turn_id=turn_id,
                route="fast" if fast else "brain",
                action=route.action if fast else None,
                score=route.score,
            )
        )

        if fast:
            async with self._stage(turn_id, "action"):
                spoken = await self.actions.get(route.action).run(route.args)
            reply = BrainReply(spoken=spoken)
        else:
            async with self._stage(turn_id, "ack"):
                await self.tts.speak(ACK)
            async with self._stage(turn_id, "brain"):
                reply = await self.brain.ask(BrainRequest(turn_id, transcript.text))

        await self.bus.publish(
            Answered(turn_id=turn_id, spoken=reply.spoken, detail=reply.detail)
        )
        async with self._stage(turn_id, "speak"):
            await self.tts.speak(reply.spoken)
        return "answered"

    @asynccontextmanager
    async def _stage(self, turn_id: str, stage: str) -> AsyncIterator[None]:
        started = now()
        try:
            yield
        finally:
            await self.bus.publish(
                StageTimed(turn_id=turn_id, stage=stage, started=started, ended=now())
            )
