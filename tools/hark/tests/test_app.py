"""The whole app with only audio and ``claude`` faked.

Real: bus, turn log, event stream, rules router, resources, safety gate,
gate socket, the pre-tool hook script, the settings file, ``ClaudeBrain``
and its child process. The fake child runs the hook from ``--settings`` the
way Claude Code does, so a passing test means the socket path really reached
the child through the environment.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import socket
import sys
import tempfile
from pathlib import Path

import pytest

from hark.actions.open_resource import load_resources
from hark.app import NO_BRAIN, App, GuardedBrain, Paths, ServerDown, check_servers, serve, write_claude_settings
from hark.brain.claude import BrainUnavailable, ClaudeBrain
from hark.gate.settings import hook_timeout
from hark.ports import Brain, BrainRequest, Wake
from hark.stubs import StubSpeechToText, StubTextToSpeech, StubWakeWord

FAKE = Path(__file__).parent / "fakes" / "fake_claude.py"

RESOURCES = """
[[resource]]
name = "labs_github"
spoken = "the labs GitHub page"
url = "https://example.com/labs"
phrases = ["open my labs GitHub page", "open labs github"]
"""


@pytest.fixture
def paths():
    # Unix socket paths must stay under 104 bytes, so not pytest's long tmp_path.
    with tempfile.TemporaryDirectory(prefix="hk", dir="/tmp") as d:
        root = Path(d)
        (root / "actions.toml").write_text(RESOURCES)
        yield Paths(
            gate_socket=root / "gate.sock",
            event_socket=root / "events.sock",
            turn_log=root / "turns.jsonl",
            actions=root / "actions.toml",
            claude_settings=root / "claude-settings.json",
            audio_config=root / "audio.toml",
            gate_config=root / "gate.toml",
        )


class Opened:
    def __init__(self) -> None:
        self.argv: list[list[str]] = []

    async def __call__(self, argv):
        self.argv.append(list(argv))
        return 0


def make_app(paths: Paths, utterances, wake=None, opener=None) -> App:
    settings = write_claude_settings(paths.claude_settings)
    brain = ClaudeBrain(
        settings,
        command=(sys.executable, str(FAKE)),
        env={"HARK_GATE_SOCKET": str(paths.gate_socket)},
    )
    return App(
        wake=wake or StubWakeWord(),
        stt=StubSpeechToText(utterances),
        tts=StubTextToSpeech(),
        actions=load_resources(paths.actions, opener=opener or Opened()),
        brain=brain,
        paths=paths,
    )


async def run_turns(app: App, turns: int) -> None:
    await app.start()
    try:
        await app.run(turns=turns)
    finally:
        await app.stop()


def log_lines(paths: Paths) -> list[dict]:
    return [json.loads(line) for line in paths.turn_log.read_text().splitlines()]


def summaries(paths: Paths) -> list[dict]:
    return [line for line in log_lines(paths) if line["type"] == "TurnSummary"]


def test_fast_turn_opens_the_resource_and_logs_it(paths):
    opened = Opened()
    app = make_app(paths, ["Open my labs GitHub page."], opener=opened)
    asyncio.run(run_turns(app, 1))
    assert opened.argv == [["open", "https://example.com/labs"]]
    assert app.tts.spoken == ["Opening the labs GitHub page."]
    [summary] = summaries(paths)
    assert summary["route"] == "fast" and summary["action"] == "labs_github"
    assert summary["r6_latency"] is not None


def test_brain_turn_with_a_safe_call_runs_unasked(paths):
    app = make_app(paths, ["tool:git status"])
    asyncio.run(run_turns(app, 1))
    assert app.tts.spoken == ["On it.", "Ran git status."]
    kinds = [line["type"] for line in log_lines(paths)]
    assert "ToolCallRequested" in kinds and "ConfirmationAsked" not in kinds


def test_dangerous_call_asks_and_a_spoken_no_blocks_it(paths):
    app = make_app(paths, ["tool:git push", "no"])
    asyncio.run(run_turns(app, 1))
    assert app.tts.spoken[0] == "On it."
    assert app.tts.spoken[1].startswith("Allow:") and app.tts.spoken[1].endswith("Say yes or no.")
    assert app.tts.spoken[2].startswith("Denied: you said no")
    lines = log_lines(paths)
    turn_id = lines[0]["turn_id"]
    gate = [line for line in lines if line["type"].startswith(("ToolCall", "Confirmation"))]
    assert [line["type"] for line in gate] == [
        "ToolCallRequested", "ConfirmationAsked", "ConfirmationAnswered", "ToolCallDecided",
    ]  # fmt: skip
    assert all(line["turn_id"] == turn_id for line in gate)  # the gate saw the live turn
    assert gate[-1]["allowed"] is False
    assert summaries(paths)[0]["route"] == "brain"


def test_silence_blocks_and_a_yes_allows(paths):
    app = make_app(paths, ["tool:rm notes.txt", None, "tool:rm notes.txt", "yes"])
    asyncio.run(run_turns(app, 2))
    decided = [line for line in log_lines(paths) if line["type"] == "ToolCallDecided"]
    assert [d["allowed"] for d in decided] == [False, True]
    assert app.tts.spoken[-1] == "Ran rm notes.txt."


def test_wake_with_no_speech_ends_the_turn(paths):
    app = make_app(paths, [None])
    asyncio.run(run_turns(app, 1))
    assert summaries(paths)[0]["outcome"] == "no_speech"


def test_stop_leaves_no_socket_and_no_child(paths):
    app = make_app(paths, ["pid"])

    async def scenario():
        await app.start()
        assert paths.gate_socket.exists() and paths.event_socket.exists()
        await app.run(turns=1)
        pid = int(app.tts.spoken[-1])
        os.kill(pid, 0)  # alive between turns
        await app.stop()
        return pid

    pid = asyncio.run(scenario())
    assert not paths.gate_socket.exists() and not paths.event_socket.exists()
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_a_second_instance_refuses_and_leaves_the_first_alone(paths):
    async def scenario():
        first = make_app(paths, [])
        await first.start()
        try:
            second = make_app(paths, [])
            with pytest.raises(RuntimeError, match="already listening"):
                await second.start()
            await second.stop()
            assert paths.gate_socket.exists()  # the first instance's socket survives
        finally:
            await first.stop()

    asyncio.run(scenario())


def test_the_event_socket_alone_also_refuses(paths):
    async def scenario():
        first = make_app(paths, [])
        await first.start()
        try:
            other = Paths(**{**paths.__dict__, "gate_socket": paths.gate_socket.with_name("g2.sock")})
            second = make_app(other, [])
            with pytest.raises(RuntimeError, match="already streaming"):
                await second.start()
            await second.stop()
            assert not other.gate_socket.exists()  # the half-started instance cleaned up
        finally:
            await first.stop()

    asyncio.run(scenario())


def test_event_stream_clients_see_the_turn(paths):
    async def scenario():
        app = make_app(paths, ["Open labs github"])
        await app.start()
        reader, writer = await asyncio.open_unix_connection(str(paths.event_socket))
        while not app.stream._clients:  # the server registers the client on its next tick
            await asyncio.sleep(0.01)
        await app.run(turns=1)
        await app.bus.drain()
        seen = []
        while not seen or seen[-1]["type"] != "TurnEnded":
            seen.append(json.loads(await asyncio.wait_for(reader.readline(), 2)))
        writer.close()
        await app.stop()
        return [e["type"] for e in seen]

    kinds = asyncio.run(scenario())
    assert kinds[0] == "TurnStarted" and kinds[-1] == "TurnEnded"


class BlockingWake:
    async def wait(self) -> Wake:
        await asyncio.Event().wait()
        raise AssertionError("unreachable")


def test_sigterm_stops_cleanly(paths):
    app = make_app(paths, [], wake=BlockingWake())

    async def scenario():
        task = asyncio.create_task(serve(app))
        for _ in range(100):
            if paths.gate_socket.exists() and paths.event_socket.exists():
                break
            await asyncio.sleep(0.01)
        os.kill(os.getpid(), signal.SIGTERM)
        await asyncio.wait_for(task, 5)

    asyncio.run(scenario())
    assert not paths.gate_socket.exists() and not paths.event_socket.exists()


def test_unreachable_brain_is_said_aloud():
    class Down:
        async def ask(self, request):
            raise BrainUnavailable("no claude")

    guarded = GuardedBrain(Down())
    assert isinstance(guarded, Brain)
    reply = asyncio.run(guarded.ask(BrainRequest("t", "hi")))
    assert reply.spoken == NO_BRAIN


def test_missing_claude_still_serves_fixed_commands(paths):
    app = make_app(paths, ["what time is it", "open labs github"])
    app.brain = ClaudeBrain(paths.claude_settings, command=("/nonexistent/claude",), backoff=(0,))
    app.runner.brain = GuardedBrain(app.brain)
    asyncio.run(run_turns(app, 2))
    assert app.tts.spoken == ["On it.", NO_BRAIN, "Opening the labs GitHub page."]


def test_settings_file_is_regenerated_with_the_hook(paths):
    paths.claude_settings.write_text("stale")
    write_claude_settings(paths.claude_settings)
    hook = json.loads(paths.claude_settings.read_text())["hooks"]["PreToolUse"][0]["hooks"][0]
    assert "pretool_hook.py" in hook["command"]
    assert hook["timeout"] == hook_timeout() and hook["onFailure"] == "block"


def test_speech_server_down_is_named():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        up = f"http://127.0.0.1:{s.getsockname()[1]}/v1"
        with socket.socket() as free:
            free.bind(("127.0.0.1", 0))
            down = f"http://127.0.0.1:{free.getsockname()[1]}/v1"
        check_servers({"whisper": up}, wait=0)
        with pytest.raises(ServerDown, match="kokoro"):
            check_servers({"whisper": up, "kokoro": down}, wait=0)
