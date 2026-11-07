"""Spoken-yes checks (F6, F8) and the gate's event sequence."""

from __future__ import annotations

import asyncio
from collections import deque

import pytest

from hark.events import ConfirmationAnswered, ConfirmationAsked, ToolCallDecided, ToolCallRequested
from hark.gate.classify import Kind, Verdict
from hark.gate.config import GateConfig
from hark.gate.confirm import RETRY_PROMPT, Answer, Confirmer, judge
from hark.gate.gate import HarkSafetyGate
from hark.ports import SafetyGate, ToolCall, Transcript
from hark.stubs import InMemoryEventBus, StubSafetyGate, StubTextToSpeech

CONFIG = GateConfig(min_energy=0.03, window_s=5.0)


class ScriptedSTT:
    """Plays (text, energy) pairs; None is silence. Counts listens."""

    def __init__(self, *answers: tuple[str, float | None] | None) -> None:
        self._answers = deque(answers)
        self.listens = 0

    async def listen(self, timeout: float | None = None) -> Transcript | None:
        self.listens += 1
        item = self._answers.popleft() if self._answers else None
        if item is None:
            return None
        text, energy = item
        return Transcript(text=text, speech_ended_at=0.0, energy=energy)


def confirm(*answers):
    tts, stt = StubTextToSpeech(), ScriptedSTT(*answers)
    result = asyncio.run(Confirmer(tts, stt, CONFIG).confirm())
    return result, tts, stt


def t(text, energy=0.2):
    return Transcript(text=text, speech_ended_at=0.0, energy=energy)


# --- judge: the F6 checks, one at a time ------------------------------------


@pytest.mark.parametrize("text", ["yes", "Yes.", "YEAH!", " yep ", "Do it.", "go ahead", "Confirm"])
def test_yes_words_at_good_energy_confirm(text):
    assert judge(t(text), CONFIG) is Answer.YES


@pytest.mark.parametrize("energy", [0.0, 0.5, 1.0, None])
def test_thank_you_never_confirms(energy):
    assert judge(t("Thank you.", energy), CONFIG) is not Answer.YES


@pytest.mark.parametrize("text", ["thanks for watching", "you", "bye", "okay"])
def test_hallucination_phrases_never_confirm(text):
    assert judge(t(text), CONFIG) is Answer.UNCLEAR


def test_yes_below_the_floor_is_unclear():
    assert judge(t("yes", 0.029), CONFIG) is Answer.UNCLEAR
    assert judge(t("yes", 0.03), CONFIG) is Answer.YES


def test_none_energy_is_not_confirmed():
    assert judge(t("yes", None), CONFIG) is Answer.UNCLEAR


@pytest.mark.parametrize("text", ["yess", "yeah right", "guess", "yes please", "yes no", "yea", "ye s", "no yes"])
def test_near_matches_are_not_a_yes(text):
    assert judge(t(text), CONFIG) is not Answer.YES


@pytest.mark.parametrize("text", ["no", "No.", "nope", "cancel"])
def test_no_denies_even_when_quiet(text):
    assert judge(t(text, 0.0), CONFIG) is Answer.NO
    assert judge(t(text, None), CONFIG) is Answer.NO


def test_a_phrase_on_both_lists_is_not_a_yes():
    cfg = GateConfig(yes_phrases=("yes", "okay"), min_energy=0.03)
    assert judge(t("okay"), cfg) is Answer.UNCLEAR


# --- the flow ----------------------------------------------------------------


def test_yes_confirms_without_retry():
    result, tts, stt = confirm(("yes", 0.2))
    assert result.confirmed and result.outcome == "yes"
    assert tts.spoken == [] and stt.listens == 1


def test_thank_you_then_silence_denies():
    result, tts, _ = confirm(("Thank you.", 0.5), None)
    assert not result.confirmed
    assert tts.spoken == [RETRY_PROMPT]


def test_quiet_yes_asks_again_then_denies():
    result, tts, stt = confirm(("yes", 0.001), ("yes", 0.001))
    assert not result.confirmed and result.outcome == "unclear"
    assert tts.spoken == [RETRY_PROMPT] and stt.listens == 2


def test_none_energy_twice_denies():
    result, _, _ = confirm(("yes", None), ("yes", None))
    assert not result.confirmed


def test_silence_denies_at_once():
    result, tts, stt = confirm(None)
    assert not result.confirmed and result.outcome == "silence" and result.heard is None
    assert tts.spoken == [] and stt.listens == 1


def test_no_denies_at_once():
    result, tts, stt = confirm(("no", 0.2))
    assert not result.confirmed and result.outcome == "no"
    assert tts.spoken == [] and stt.listens == 1


def test_second_attempt_succeeds():
    result, tts, stt = confirm(("thank you", 0.2), ("yes", 0.2))
    assert result.confirmed and tts.spoken == [RETRY_PROMPT] and stt.listens == 2


def test_only_one_retry():
    result, _, stt = confirm(("hmm", 0.2), ("what", 0.2), ("yes", 0.2))
    assert not result.confirmed and stt.listens == 2


def test_a_listener_that_hangs_is_cut_off():
    class Hangs:
        async def listen(self, timeout=None):
            await asyncio.sleep(60)

    cfg = GateConfig(window_s=0.2)
    result = asyncio.run(Confirmer(StubTextToSpeech(), Hangs(), cfg).confirm())
    assert not result.confirmed and result.outcome == "silence"


# --- the gate ----------------------------------------------------------------


def push() -> ToolCall:
    return ToolCall("turn-1", "Bash", {"command": "git push"})


def ls() -> ToolCall:
    return ToolCall("turn-1", "Bash", {"command": "ls"})


def build(*answers, classifier=None):
    bus, tts, stt = InMemoryEventBus(), StubTextToSpeech(), ScriptedSTT(*answers)
    kwargs = {"classifier": classifier} if classifier else {}
    gate = HarkSafetyGate(bus, tts, stt, confirmer=Confirmer(tts, stt, CONFIG), **kwargs)
    return gate, bus, tts, stt


def names(bus):
    return [type(e).__name__ for e in bus.events]


def test_gate_satisfies_the_port():
    gate, *_ = build()
    assert isinstance(gate, SafetyGate)


def test_allow_path_is_instant_and_silent():
    gate, bus, tts, stt = build()
    decision = asyncio.run(gate.check(ls()))
    assert decision.allowed
    assert names(bus) == ["ToolCallRequested", "ToolCallDecided"]
    assert tts.spoken == [] and stt.listens == 0


def test_ask_path_event_sequence_matches_the_stub():
    gate, bus, tts, _ = build(("yes", 0.2))
    decision = asyncio.run(gate.check(push()))
    assert decision.allowed and decision.reason == "you said yes"

    stub_bus = InMemoryEventBus()
    from hark.stubs import StubSpeechToText

    stub = StubSafetyGate(stub_bus, StubTextToSpeech(), StubSpeechToText(["yes"]), needs_yes=lambda c: True)
    asyncio.run(stub.check(push()))
    assert names(bus) == names(stub_bus) == [
        "ToolCallRequested", "ConfirmationAsked", "ConfirmationAnswered", "ToolCallDecided",
    ]  # fmt: skip
    asked = next(e for e in bus.events if isinstance(e, ConfirmationAsked))
    assert asked.prompt == "Allow: push to a remote with git? Say yes or no."
    assert tts.spoken == [asked.prompt]


@pytest.mark.parametrize(
    ("answers", "sentence"),
    [
        ([("no", 0.2)], "Denied: you said no to a request to push to a remote with git."),
        ([None], "Denied: there was no spoken yes to a request to push to a remote with git."),
        (
            [("Thank you.", 0.5), None],
            "Denied: there was no spoken yes to a request to push to a remote with git.",
        ),
        (
            [("Thank you.", 0.5), ("Thank you.", 0.5)],
            "Denied: I did not hear a clear yes to a request to push to a remote with git.",
        ),
    ],
)
def test_denials_are_plain_sentences(answers, sentence):
    gate, bus, *_ = build(*answers)
    decision = asyncio.run(gate.check(push()))
    assert not decision.allowed and decision.reason == sentence
    answered = next(e for e in bus.events if isinstance(e, ConfirmationAnswered))
    assert answered.confirmed is False
    decided = next(e for e in bus.events if isinstance(e, ToolCallDecided))
    assert decided.reason == sentence and not decided.allowed


def test_requested_event_carries_the_command_even_when_denied():
    gate, bus, *_ = build(("no", 0.2))
    asyncio.run(gate.check(push()))
    requested = next(e for e in bus.events if isinstance(e, ToolCallRequested))
    assert requested.input == {"command": "git push"} and requested.turn_id == "turn-1"


def test_a_broken_classifier_asks():
    def boom(call):
        raise RuntimeError("bug")

    gate, bus, tts, _ = build(("no", 0.2), classifier=boom)
    decision = asyncio.run(gate.check(ls()))
    assert not decision.allowed and tts.spoken  # asked, did not allow


def test_a_failing_speaker_denies_and_still_reports():
    class BrokenTTS:
        async def speak(self, text):
            raise OSError("no audio device")

    bus, stt = InMemoryEventBus(), ScriptedSTT(("yes", 0.2))
    gate = HarkSafetyGate(bus, BrokenTTS(), stt, confirmer=Confirmer(BrokenTTS(), stt, CONFIG))
    decision = asyncio.run(gate.check(push()))
    assert not decision.allowed
    assert names(bus)[-1] == "ToolCallDecided"


def test_a_classifier_that_allows_is_trusted_only_for_allow():
    gate, _, tts, _ = build(classifier=lambda c: Verdict(Kind.ALLOW, "test"))
    assert asyncio.run(gate.check(push())).allowed and tts.spoken == []


def test_ports_are_untouched():
    import subprocess
    from pathlib import Path

    here = Path(__file__).parent
    root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=here, capture_output=True, text=True, check=True
    ).stdout.strip()
    diff = subprocess.run(
        ["git", "diff", "--name-only", "main", "--", "tools/hark/hark/ports", "tools/hark/hark/events.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    assert diff.stdout == ""
