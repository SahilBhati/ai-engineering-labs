"""ClaudeBrain against a fake child that speaks the recorded stream-JSON protocol."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
from pathlib import Path

import pytest

from hark.brain import BrainUnavailable, ClaudeBrain, parse_line, split_reply
from hark.ports import Brain, BrainReply, BrainRequest

FAKE = Path(__file__).parent / "fakes" / "fake_claude.py"
COMMAND = (sys.executable, str(FAKE))


def make(tmp_path: Path, **kwargs) -> ClaudeBrain:
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    kwargs.setdefault("command", COMMAND)
    kwargs.setdefault("cwd", tmp_path)
    return ClaudeBrain(settings, **kwargs)


async def ask(brain: ClaudeBrain, text: str) -> BrainReply:
    return await brain.ask(BrainRequest("t", text))


async def pid_of(brain: ClaudeBrain) -> int:
    return int((await ask(brain, "pid")).spoken)


def run(coro):
    return asyncio.run(coro)


def test_is_a_brain(tmp_path):
    assert isinstance(make(tmp_path), Brain)


def test_normal_turn_and_flags(tmp_path, monkeypatch):
    argv_file = tmp_path / "argv.json"
    cwd_file = tmp_path / "cwd.txt"
    monkeypatch.setenv("FAKE_ARGV_FILE", str(argv_file))
    monkeypatch.setenv("FAKE_CWD_FILE", str(cwd_file))

    async def go():
        brain = make(tmp_path, model="opus")
        try:
            return await ask(brain, "You have 3 sessions.")
        finally:
            await brain.aclose()

    reply = run(go())
    assert reply == BrainReply(spoken="You have 3 sessions.", detail=None)
    argv = json.loads(argv_file.read_text())
    assert argv[:1] == ["-p"]
    for flag in ("--input-format", "--output-format"):
        assert argv[argv.index(flag) + 1] == "stream-json"
    assert {"--verbose", "--include-partial-messages"} <= set(argv)
    assert argv[argv.index("--settings") + 1] == str(tmp_path / "settings.json")
    assert argv[argv.index("--model") + 1] == "opus"
    assert "DETAIL:" in argv[argv.index("--append-system-prompt") + 1]
    for banned in ("--allowedTools", "--dangerously-skip-permissions"):
        assert banned not in argv
    assert Path(cwd_file.read_text()).resolve() == tmp_path.resolve()


def test_env_reaches_the_child_on_top_of_the_inherited_one(tmp_path, monkeypatch):
    # The fake writes its cwd to FAKE_CWD_FILE: proof the variable got through.
    cwd_file = tmp_path / "cwd.txt"
    monkeypatch.delenv("FAKE_CWD_FILE", raising=False)

    async def go():
        brain = make(tmp_path, env={"FAKE_CWD_FILE": str(cwd_file)})
        try:
            return await ask(brain, "hi")
        finally:
            await brain.aclose()

    assert run(go()).spoken == "hi"  # PATH etc. still inherited, or the child wouldn't start
    assert cwd_file.exists()


def test_one_process_serves_many_turns(tmp_path):
    async def go():
        brain = make(tmp_path)
        try:
            return [await pid_of(brain) for _ in range(3)]
        finally:
            await brain.aclose()

    assert len(set(run(go()))) == 1


def test_detail_marker_splits(tmp_path):
    async def go():
        brain = make(tmp_path)
        try:
            return await ask(brain, "42 test cases.\nDETAIL:\nlabs: 30\nhark: 12")
        finally:
            await brain.aclose()

    assert run(go()) == BrainReply(spoken="42 test cases.", detail="labs: 30\nhark: 12")


def test_missing_marker_speaks_first_sentences_up_to_cap():
    text = "First one. Second one is a bit longer. Third."
    reply = split_reply(text, cap=25)
    assert reply == BrainReply(spoken="First one.", detail=text)


def test_short_answer_without_marker_has_no_detail():
    assert split_reply("Done.") == BrainReply(spoken="Done.", detail=None)


def test_one_long_sentence_is_cut_on_a_word():
    reply = split_reply("word " * 100, cap=22)
    assert len(reply.spoken) <= 22 and reply.spoken.endswith("word")
    assert reply.detail is not None


def test_overlong_spoken_part_moves_to_detail():
    reply = split_reply("Short one. " + "x" * 50 + ".\nDETAIL: more", cap=20)
    assert reply.spoken == "Short one."
    assert "more" in reply.detail and "x" * 50 in reply.detail


def test_unknown_events_ignored(tmp_path):
    async def go():
        brain = make(tmp_path)
        try:
            return await ask(brain, "unknown")
        finally:
            await brain.aclose()

    assert run(go()).spoken == "fine."


def test_parse_line_ignores_unknown_and_garbage():
    assert parse_line("not json") is None
    assert parse_line('[1,2]') is None
    assert parse_line('{"type":"future_thing"}') is None
    assert parse_line('{"type":"stream_event","event":{"type":"brand_new"}}') is None
    assert parse_line('{"type":"result","result":"hi","is_error":false}').text == "hi"


def test_error_result_apologises(tmp_path):
    async def go():
        brain = make(tmp_path)
        try:
            return await ask(brain, "error")
        finally:
            await brain.aclose()

    reply = run(go())
    assert reply.spoken.startswith("Sorry") and reply.detail == "boom"


def test_child_dies_mid_turn_then_next_turn_works(tmp_path):
    async def go():
        brain = make(tmp_path)
        try:
            first = await pid_of(brain)
            lost = await ask(brain, "die")  # child exits mid-turn
            again = await pid_of(brain)
            return first, lost, again
        finally:
            await brain.aclose()

    first, lost, again = run(go())
    assert lost == BrainReply(spoken="Sorry, I lost that one. Try again.")
    assert again != first


def test_external_kill_between_turns_restarts(tmp_path):
    async def go():
        brain = make(tmp_path)
        try:
            first = await pid_of(brain)
            os.kill(first, signal.SIGKILL)
            await asyncio.sleep(0.2)
            return first, await pid_of(brain)
        finally:
            await brain.aclose()

    first, second = run(go())
    assert second != first


def test_external_kill_just_before_turn_loses_only_that_turn(tmp_path):
    async def go():
        brain = make(tmp_path)
        try:
            first = await pid_of(brain)
            os.kill(first, signal.SIGKILL)  # not yet reaped: looks alive
            lost = await ask(brain, "hi")
            return lost, await pid_of(brain), first
        finally:
            await brain.aclose()

    lost, second, first = run(go())
    assert lost.spoken.startswith("Sorry, I lost")
    assert second != first


def test_repeated_start_failure_raises(tmp_path):
    sleeps: list[float] = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    async def go():
        brain = make(
            tmp_path,
            command=("/nonexistent/claude",),
            max_start_failures=4,
            sleep=fake_sleep,
        )
        await ask(brain, "hi")

    with pytest.raises(BrainUnavailable):
        run(go())
    assert sleeps == [1, 2, 4]  # backs off between tries, not after the last


def test_backoff_caps_at_30(tmp_path):
    sleeps: list[float] = []

    async def fake_sleep(delay):
        sleeps.append(delay)

    async def go():
        await ask(
            make(tmp_path, command=("/nonexistent/claude",), max_start_failures=9, sleep=fake_sleep),
            "hi",
        )

    with pytest.raises(BrainUnavailable):
        run(go())
    assert sleeps == [1, 2, 4, 8, 16, 30, 30, 30]


def test_rollover_by_turn_count(tmp_path):
    async def go():
        brain = make(tmp_path, max_turns=2)
        try:
            return [await pid_of(brain) for _ in range(4)]
        finally:
            await brain.aclose()

    a, b, c, d = run(go())
    assert a == b and c == d and a != c


def test_rollover_by_idle_time(tmp_path):
    now = [100.0]

    async def go():
        brain = make(tmp_path, max_idle=60, clock=lambda: now[0])
        try:
            first = await pid_of(brain)
            now[0] += 30
            same = await pid_of(brain)
            now[0] += 61
            fresh = await pid_of(brain)
            return first, same, fresh
        finally:
            await brain.aclose()

    first, same, fresh = run(go())
    assert first == same and fresh != first


def test_timeout_kills_restarts_and_apologises(tmp_path):
    async def go():
        brain = make(tmp_path, turn_timeout=0.5)
        try:
            first = await pid_of(brain)
            slow = await ask(brain, "hang")
            return first, slow, await pid_of(brain)
        finally:
            await brain.aclose()

    first, slow, after = run(go())
    assert slow == BrainReply(spoken="That took too long.")
    assert after != first


def test_fake_turn_with_real_brain_in_place_of_stub(tmp_path):
    from hark.stubs import (
        InMemoryEventBus,
        StubAction,
        StubActionRegistry,
        StubRouter,
        StubSpeechToText,
        StubTextToSpeech,
        StubWakeWord,
    )
    from hark.turn import ACK, TurnRunner

    async def go():
        bus = InMemoryEventBus()
        tts = StubTextToSpeech()
        registry = StubActionRegistry([StubAction("open_labs", ["open labs"], reply="Opened.")])
        brain = make(tmp_path)
        runner = TurnRunner(
            wake=StubWakeWord(),
            stt=StubSpeechToText(["how many claude sessions are running"]),
            router=StubRouter(registry),
            actions=registry,
            brain=brain,
            tts=tts,
            bus=bus,
        )
        try:
            await runner.run_once()
        finally:
            await brain.aclose()
        return bus, tts

    bus, tts = run(go())
    assert tts.spoken[0] == ACK
    assert tts.spoken[1] == "how many claude sessions are running"
    assert [type(e).__name__ for e in bus.events][-1] == "TurnEnded"
    assert any(type(e).__name__ == "Answered" for e in bus.events)
