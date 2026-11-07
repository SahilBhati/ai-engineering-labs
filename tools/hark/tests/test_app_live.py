"""The app with the real ``claude``: only audio is faked.

    uv run pytest -m live

Unlike ``test_gate_live.py`` the child runs exactly as the app starts it:
``ClaudeBrain``'s argv, no ``--allowedTools``, the socket passed in ``env``.
So a safe command that runs proves the hook's allow stands in for Claude
Code's own permission prompt, and a delete that survives proves the gate,
not a missing permission, stopped it.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from hark.actions.registry import Registry
from hark.app import App, Paths, write_claude_settings
from hark.brain.claude import ClaudeBrain
from hark.stubs import StubSpeechToText, StubTextToSpeech, StubWakeWord

pytestmark = pytest.mark.live

MODEL = os.environ.get("HARK_LIVE_MODEL", "haiku")


@pytest.fixture(autouse=True)
def need_claude():
    if shutil.which("claude") is None:
        pytest.skip("claude CLI not found")


@pytest.fixture
def work():
    with tempfile.TemporaryDirectory(prefix="hk", dir="/tmp") as d:
        yield Path(d)


def make_app(work: Path, utterances) -> App:
    paths = Paths(
        gate_socket=work / "gate.sock",
        event_socket=work / "events.sock",
        turn_log=work / "turns.jsonl",
        actions=work / "actions.toml",
        claude_settings=work / "claude-settings.json",
    )
    settings = write_claude_settings(paths.claude_settings)
    brain = ClaudeBrain(
        settings, model=MODEL, cwd=work, env={"HARK_GATE_SOCKET": str(paths.gate_socket)}
    )
    return App(
        wake=StubWakeWord(), stt=StubSpeechToText(utterances), tts=StubTextToSpeech(),
        actions=Registry(), brain=brain, paths=paths,
    )  # fmt: skip


def run(app: App) -> list[dict]:
    async def go():
        await app.start()
        try:
            await app.run(turns=1)
        finally:
            await app.stop()

    asyncio.run(go())
    return [json.loads(line) for line in app.paths.turn_log.read_text().splitlines()]


def test_safe_command_runs_without_asking(work):
    (work / "a.txt").write_text("x")
    (work / "b.txt").write_text("x")
    app = make_app(work, ["Use the Bash tool to run ls in the current folder and tell me how many .txt files there are."])
    events = run(app)
    decided = [e for e in events if e["type"] == "ToolCallDecided"]
    assert decided and all(e["allowed"] for e in decided)
    assert not [e for e in events if e["type"] == "ConfirmationAsked"]
    assert "2" in app.tts.spoken[-1] or "two" in app.tts.spoken[-1].lower()


def test_spoken_no_keeps_the_file(work):
    target = work / "keep.txt"
    target.write_text("x")
    app = make_app(work, ["Delete the file keep.txt in the current folder with rm.", "no"])
    events = run(app)
    assert target.exists()
    asked = [e for e in events if e["type"] == "ConfirmationAsked"]
    assert asked and all(e["turn_id"] == events[0]["turn_id"] for e in asked)
    assert any(not e["allowed"] for e in events if e["type"] == "ToolCallDecided")
