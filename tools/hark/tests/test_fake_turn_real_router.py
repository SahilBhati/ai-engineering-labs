"""The fake turn again, with the real router and registry in place of the stubs."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from hark import ports
from hark.actions import OpenResource, Registry
from hark.ports import BrainReply
from hark.router import RulesRouter
from hark.stubs import (
    InMemoryEventBus,
    StubBrain,
    StubSafetyGate,
    StubSpeechToText,
    StubTextToSpeech,
    StubWakeWord,
)
from hark.turn import ACK, TurnRunner


class FakeOpener:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def __call__(self, argv: Sequence[str]) -> int:
        self.calls.append(list(argv))
        return 0


def build(utterances: list[str | None]):
    bus = InMemoryEventBus()
    stt = StubSpeechToText(utterances)
    tts = StubTextToSpeech()
    opener = FakeOpener()
    registry = Registry(
        [
            OpenResource(
                "labs_github",
                ["open my AI Engineering Labs GitHub page", "open labs github"],
                ["open", "https://github.com/example-user/example-repo"],
                spoken="the labs GitHub page",
                opener=opener,
            )
        ]
    )
    runner = TurnRunner(
        wake=StubWakeWord(),
        stt=stt,
        router=RulesRouter(registry),
        actions=registry,
        brain=StubBrain(StubSafetyGate(bus, tts, stt), reply=BrainReply(spoken="Done.")),
        tts=tts,
        bus=bus,
    )
    return runner, bus, tts, opener


def test_real_adapters_satisfy_ports():
    runner, _, _, _ = build([])
    assert isinstance(runner.router, ports.Router)
    assert isinstance(runner.actions, ports.ActionRegistry)
    assert isinstance(runner.actions.get("labs_github"), ports.Action)


def test_fast_turn_opens_the_url():
    runner, bus, tts, opener = build(["Open my AI Engineering Labs GitHub page."])
    asyncio.run(runner.run_once())

    routed = next(e for e in bus.events if type(e).__name__ == "Routed")
    assert routed.route == "fast" and routed.action == "labs_github"
    assert opener.calls == [["open", "https://github.com/example-user/example-repo"]]
    assert tts.spoken == ["Opening the labs GitHub page."]
    assert bus.events[-1].outcome == "answered"


def test_near_miss_goes_to_the_brain():
    runner, bus, tts, opener = build(["open labs github and delete the build"])
    asyncio.run(runner.run_once())

    routed = next(e for e in bus.events if type(e).__name__ == "Routed")
    assert routed.route == "brain" and routed.action is None
    assert 0 < routed.score < 0.85
    assert opener.calls == []
    assert tts.spoken == [ACK, "Done."]
