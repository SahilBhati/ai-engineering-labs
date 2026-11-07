"""A fake turn, as text, through every port's stub: proves the contracts fit."""

from __future__ import annotations

import asyncio
import json

import pytest

from hark import ports
from hark.events import StageTimed, Transcribed, TurnStarted
from hark.ports import BrainReply, ToolCall
from hark.stubs import (
    InMemoryEventBus,
    StubAction,
    StubActionRegistry,
    StubBrain,
    StubRouter,
    StubSafetyGate,
    StubSpeechToText,
    StubTextToSpeech,
    StubWakeWord,
)
from hark.turn import ACK, TurnRunner


def is_push(call: ToolCall) -> bool:
    return call.tool == "Bash" and "git push" in call.input.get("command", "")


def build(utterances: list[str | None]):
    bus = InMemoryEventBus()
    stt = StubSpeechToText(utterances)
    tts = StubTextToSpeech()
    gate = StubSafetyGate(bus, tts, stt, needs_yes=is_push)
    open_labs = StubAction("open_labs", ["open labs"], reply="Opened.")
    registry = StubActionRegistry([open_labs])
    brain = StubBrain(
        gate,
        reply=BrainReply(spoken="Pushed.", detail="main -> origin/main"),
        tool_calls=[
            ("Bash", {"command": "git status"}),
            ("Bash", {"command": "git push"}),
        ],
    )
    runner = TurnRunner(
        wake=StubWakeWord(),
        stt=stt,
        router=StubRouter(registry),
        actions=registry,
        brain=brain,
        tts=tts,
        bus=bus,
    )
    return runner, bus, tts, open_labs


def run(runner: TurnRunner) -> str:
    return asyncio.run(runner.run_once())


def sequence(bus: InMemoryEventBus) -> list[str]:
    return [type(e).__name__ for e in bus.events]


def assert_well_formed(bus: InMemoryEventBus, turn_id: str, stages: list[str]) -> None:
    events = bus.events
    assert all(e.turn_id == turn_id for e in events)
    assert [e.ts for e in events] == sorted(e.ts for e in events)
    timed = [e for e in events if isinstance(e, StageTimed)]
    assert [t.stage for t in timed] == stages
    assert all(t.duration >= 0 for t in timed)
    json.dumps([e.to_dict() for e in events])  # streamable as JSON lines


def test_stubs_satisfy_ports():
    runner, bus, tts, _ = build([])
    pairs = [
        (runner.wake, ports.WakeWord),
        (runner.stt, ports.SpeechToText),
        (runner.router, ports.Router),
        (runner.actions, ports.ActionRegistry),
        (runner.actions.get("open_labs"), ports.Action),
        (runner.brain, ports.Brain),
        (runner.brain._gate, ports.SafetyGate),
        (tts, ports.TextToSpeech),
        (bus, ports.EventBus),
    ]
    for stub, port in pairs:
        assert isinstance(stub, port), f"{type(stub).__name__} is not a {port.__name__}"


def test_fast_turn():
    runner, bus, tts, open_labs = build(["Open labs"])
    turn_id = run(runner)

    assert sequence(bus) == [
        "TurnStarted",
        "StageTimed",  # listen
        "Transcribed",
        "StageTimed",  # route
        "Routed",
        "StageTimed",  # action
        "Answered",
        "StageTimed",  # speak
        "TurnEnded",
    ]
    assert_well_formed(bus, turn_id, ["listen", "route", "action", "speak"])
    assert bus.events[4].route == "fast" and bus.events[4].action == "open_labs"
    assert open_labs.runs == [{}]
    assert tts.spoken == ["Opened."]


def test_brain_turn_with_confirmed_push():
    runner, bus, tts, open_labs = build(["push my branch", "yes"])
    turn_id = run(runner)

    assert sequence(bus) == [
        "TurnStarted",
        "StageTimed",  # listen
        "Transcribed",
        "StageTimed",  # route
        "Routed",
        "StageTimed",  # ack
        "ToolCallRequested",  # git status: allowed by rule
        "ToolCallDecided",
        "ToolCallRequested",  # git push: needs a spoken yes
        "ConfirmationAsked",
        "ConfirmationAnswered",
        "ToolCallDecided",
        "StageTimed",  # brain
        "Answered",
        "StageTimed",  # speak
        "TurnEnded",
    ]
    assert_well_formed(bus, turn_id, ["listen", "route", "ack", "brain", "speak"])
    assert [e.allowed for e in bus.events if type(e).__name__ == "ToolCallDecided"] == [
        True,
        True,
    ]
    assert tts.spoken == [ACK, "Allow Bash? Say yes or no.", "Pushed."]
    assert open_labs.runs == []


@pytest.mark.parametrize("answer", ["no", None])  # None: silence
def test_push_denied_on_no_or_silence(answer):
    runner, bus, tts, _ = build(["push my branch", answer])
    run(runner)

    decided = [e for e in bus.events if type(e).__name__ == "ToolCallDecided"]
    assert [d.allowed for d in decided] == [True, False]
    assert tts.spoken[-1] == "Cancelled."
    assert sequence(bus)[-1] == "TurnEnded" and bus.events[-1].outcome == "answered"


def test_no_speech_ends_turn():
    runner, bus, tts, _ = build([None])
    turn_id = run(runner)

    assert sequence(bus) == ["TurnStarted", "StageTimed", "TurnEnded"]
    assert bus.events[-1].outcome == "no_speech"
    assert tts.spoken == []
    assert_well_formed(bus, turn_id, ["listen"])


def test_r6_latency_is_measurable_from_events():
    runner, bus, _, _ = build(["Open labs"])
    run(runner)

    spoke = next(e for e in bus.events if isinstance(e, Transcribed)).speech_ended_at
    started = next(e for e in bus.events if isinstance(e, TurnStarted)).ts
    done = bus.events[-1].ts
    assert started <= spoke <= done
