"""Fail-closed and end-to-end checks against the real `claude` CLI (LAB-01 runs 02 and 04).

    uv run pytest -m live

Every run allows Bash in the permission settings (--allowedTools Bash), so any
block seen here comes from the hook. Runs use a throwaway folder and a unique
token, so "blocked" means: no successful tool result ever contained the token.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import pytest

from hark.gate.settings import hook_settings

pytestmark = pytest.mark.live

HERE = Path(__file__).parent
HOOK = HERE.parent / "hark" / "hooks" / "pretool_hook.py"
SERVER = HERE / "live" / "gate_server_process.py"
MODEL = os.environ.get("HARK_LIVE_MODEL", "haiku")


@pytest.fixture(autouse=True)
def need_claude():
    if shutil.which("claude") is None:
        pytest.skip("claude CLI not found")


@pytest.fixture
def work():
    with tempfile.TemporaryDirectory(prefix="hk", dir="/tmp") as d:
        yield Path(d)


class Session:
    """One long-running `claude -p` stream-JSON process (as the brain will be)."""

    def __init__(self, settings: dict, cwd: Path, env_extra: dict[str, str] | None = None) -> None:
        settings_file = cwd / "settings.json"
        settings_file.write_text(json.dumps(settings))
        env = {**os.environ, **(env_extra or {})}
        self.proc = subprocess.Popen(
            ["claude", "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
             "--settings", str(settings_file), "--allowedTools", "Bash", "--no-session-persistence",
             "--model", MODEL],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            cwd=cwd, env=env, text=True,
        )  # fmt: skip

    def turn(self, prompt: str, timeout: float = 120.0) -> list[dict]:
        msg = {"type": "user", "message": {"role": "user", "content": prompt}}
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        events, deadline = [], time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self.proc.stdout.readline()
            if not line:
                break
            event = json.loads(line)
            events.append(event)
            if event.get("type") == "result":
                return events
        raise AssertionError("claude did not finish the turn")

    def close(self) -> None:
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def tool_results(events: list[dict]) -> list[tuple[bool, str]]:
    out = []
    for e in events:
        if e.get("type") != "user":
            continue
        content = e.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                text = block.get("content")
                if isinstance(text, list):
                    text = " ".join(b.get("text", "") for b in text if isinstance(b, dict))
                out.append((bool(block.get("is_error")), str(text)))
    return out


def ran_with_output(events: list[dict], token: str) -> bool:
    return any(not err and token in text for err, text in tool_results(events))


def say_echo(token: str) -> str:
    return f"Run exactly this shell command and nothing else, then say done: echo {token}"


def run_once(settings: dict, cwd: Path, prompt: str, env_extra=None) -> list[dict]:
    s = Session(settings, cwd, env_extra)
    try:
        return s.turn(prompt)
    finally:
        s.close()


def test_missing_hook_script_blocks_the_call(work):
    token = f"tok{uuid.uuid4().hex[:8]}"
    events = run_once(hook_settings(work / "does-not-exist.py"), work, say_echo(token))
    assert not ran_with_output(events, token)
    assert any(err for err, _ in tool_results(events)), "expected a blocked tool result"


def test_slow_hook_past_its_timeout_blocks_the_call(work):
    slow = work / "slow.sh"
    slow.write_text("#!/bin/bash\nsleep 15\n")
    slow.chmod(0o755)
    token = f"tok{uuid.uuid4().hex[:8]}"
    settings = hook_settings(slow, timeout=3)
    settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = str(slow)
    events = run_once(settings, work, say_echo(token))
    assert not ran_with_output(events, token)


class Hark:
    def __init__(self, work: Path, answers: list) -> None:
        self.sock = work / "g.sock"
        self.events_file = work / "events.jsonl"
        self.proc = subprocess.Popen(
            [sys.executable, str(SERVER), str(self.sock), str(self.events_file), json.dumps(answers)],
            stdout=subprocess.PIPE, text=True, cwd=HERE.parent,
        )  # fmt: skip
        assert self.proc.stdout.readline().strip() == "ready"
        self.env = {"HARK_GATE_SOCKET": str(self.sock)}

    def events(self) -> list[dict]:
        if not self.events_file.exists():
            return []
        return [json.loads(l) for l in self.events_file.read_text().splitlines()]

    def kill(self) -> None:
        self.proc.send_signal(signal.SIGKILL)  # no clean shutdown: the socket file is left behind
        self.proc.wait()

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(timeout=10)


def test_allow_case_end_to_end(work):
    hark = Hark(work, [])
    try:
        token = f"tok{uuid.uuid4().hex[:8]}"
        events = run_once(hook_settings(HOOK), work, say_echo(token), hark.env)
        assert ran_with_output(events, token)
        decided = [e for e in hark.events() if e["type"] == "ToolCallDecided"]
        assert decided and all(e["allowed"] for e in decided)
        assert not [e for e in hark.events() if e["type"] == "ConfirmationAsked"]  # echo asks nothing
    finally:
        hark.close()


def test_spoken_no_keeps_the_file_and_claude_relays_the_reason(work):
    target = work / "keep-me.txt"
    target.write_text("data")
    hark = Hark(work, [["no", 0.2]] * 5)
    try:
        events = run_once(hook_settings(HOOK), work, f"Delete the file {target} with rm. If it is refused, just report why.", hark.env)
        assert target.exists()
        assert any(e["type"] == "ConfirmationAsked" for e in hark.events())
        blocked = " ".join(text for err, text in tool_results(events) if err)
        assert "Denied: you said no" in blocked
    finally:
        hark.close()


def test_spoken_yes_lets_the_delete_run(work):
    target = work / "delete-me.txt"
    target.write_text("data")
    hark = Hark(work, [["yes", 0.2]] * 5)
    try:
        run_once(hook_settings(HOOK), work, f"Delete the file {target} with rm and say done.", hark.env)
        assert not target.exists()
        assert any(e["type"] == "ConfirmationAnswered" and e["confirmed"] for e in hark.events())
    finally:
        hark.close()


def test_kill_hark_and_the_next_call_is_blocked(work):
    hark = Hark(work, [])
    session = Session(hook_settings(HOOK), work, hark.env)
    try:
        first = f"tok{uuid.uuid4().hex[:8]}"
        assert ran_with_output(session.turn(say_echo(first)), first)
        hark.kill()
        second = f"tok{uuid.uuid4().hex[:8]}"
        events = session.turn(say_echo(second))
        assert not ran_with_output(events, second)
        assert any("Hark is not running" in text for err, text in tool_results(events) if err)
    finally:
        session.close()
        hark.close()
