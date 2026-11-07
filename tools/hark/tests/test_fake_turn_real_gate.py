"""The fake turn again, with the real safety gate in place of the stub."""

from __future__ import annotations

import asyncio

from hark.events import ConfirmationAnswered, ConfirmationAsked, ToolCallDecided, ToolCallRequested
from hark.gate.confirm import Confirmer
from hark.gate.gate import HarkSafetyGate
from hark.ports import BrainReply, SafetyGate
from hark.stubs import (
    InMemoryEventBus,
    StubAction,
    StubActionRegistry,
    StubBrain,
    StubRouter,
    StubSpeechToText,
    StubTextToSpeech,
    StubWakeWord,
)
from hark.turn import TurnRunner


def build(utterances):
    bus = InMemoryEventBus()
    stt = StubSpeechToText(utterances)
    tts = StubTextToSpeech()
    gate = HarkSafetyGate(bus, tts, stt)
    registry = StubActionRegistry([StubAction("open_labs", ["open labs"], reply="Opened.")])
    brain = StubBrain(
        gate,
        reply=BrainReply(spoken="Pushed.", detail="main -> origin/main"),
        tool_calls=[("Bash", {"command": "git status"}), ("Bash", {"command": "git push"})],
    )
    runner = TurnRunner(
        wake=StubWakeWord(), stt=stt, router=StubRouter(registry), actions=registry,
        brain=brain, tts=tts, bus=bus,
    )  # fmt: skip
    return runner, bus, tts, gate


def test_real_gate_satisfies_the_port():
    assert isinstance(build([])[3], SafetyGate)


def test_status_runs_unasked_and_push_waits_for_a_yes():
    runner, bus, tts, _ = build(["Ask the brain to push.", "yes"])
    asyncio.run(runner.run_once())
    kinds = [type(e).__name__ for e in bus.events if type(e) in (ToolCallRequested, ConfirmationAsked, ConfirmationAnswered, ToolCallDecided)]
    assert kinds == [
        "ToolCallRequested", "ToolCallDecided",
        "ToolCallRequested", "ConfirmationAsked", "ConfirmationAnswered", "ToolCallDecided",
    ]  # fmt: skip
    decided = [e for e in bus.events if isinstance(e, ToolCallDecided)]
    assert [d.allowed for d in decided] == [True, True]
    assert "Allow: push to a remote with git? Say yes or no." in tts.spoken


def test_silence_denies_the_push_but_the_turn_still_ends():
    runner, bus, _, _ = build(["Ask the brain to push.", None])
    asyncio.run(runner.run_once())
    decided = [e for e in bus.events if isinstance(e, ToolCallDecided)]
    assert [d.allowed for d in decided] == [True, False]
    assert type(bus.events[-1]).__name__ == "TurnEnded"
