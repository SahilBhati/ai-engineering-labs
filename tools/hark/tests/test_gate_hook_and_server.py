"""The real hook script, as a subprocess, against a real GateServer or a fake one."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

from hark.gate.config import GateConfig
from hark.gate.confirm import Confirmer
from hark.gate.gate import HarkSafetyGate
from hark.gate.server import GateServer
from hark.gate.settings import hook_settings, hook_timeout
from hark.ports import GateDecision, ToolCall
from hark.stubs import InMemoryEventBus, StubTextToSpeech

HOOK = Path(__file__).parent.parent / "hark" / "hooks" / "pretool_hook.py"


def run_hook(stdin: str, sock: Path | str, timeout: float = 5.0) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK), "--socket", str(sock), "--timeout", str(timeout)],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=timeout + 10,
    )


def request(tool="Bash", **tool_input) -> str:
    return json.dumps({"tool_name": tool, "tool_input": tool_input or {"command": "ls"}, "session_id": "s1"})


class FakeServer:
    """A bare socket server answering with a fixed byte string (or never)."""

    def __init__(self, path: Path, reply: bytes | None) -> None:
        self.path, self.reply, self.seen = path, reply, []
        self._srv = socket.socket(socket.AF_UNIX)
        self._srv.bind(str(path))
        self._srv.listen(4)
        self._threads: list[threading.Thread] = []
        self._t = threading.Thread(target=self._loop, daemon=True)
        self._t.start()

    def _loop(self):
        while True:
            try:
                conn, _ = self._srv.accept()
            except OSError:
                return
            threading.Thread(target=self._serve, args=(conn,), daemon=True).start()

    def _serve(self, conn):
        data = b""
        while b"\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                return
            data += chunk
        self.seen.append(json.loads(data))
        if self.reply is None:
            time.sleep(30)
        else:
            conn.sendall(self.reply)
        conn.close()

    def close(self):
        self._srv.close()


@pytest.fixture
def tmp_path():
    """Shadows pytest's: macOS caps a Unix socket path at 104 bytes, and pytest's is longer."""
    with tempfile.TemporaryDirectory(prefix="hk", dir="/tmp") as d:
        yield Path(d)


@pytest.fixture
def sock(tmp_path):
    return tmp_path / "g.sock"


def serve(sock, reply):
    return FakeServer(sock, None if reply is None else (reply if isinstance(reply, bytes) else json.dumps(reply).encode() + b"\n"))


def test_allow_reply_exits_zero_with_allow_json(sock):
    srv = serve(sock, {"allow": True, "reason": "read-only command"})
    try:
        out = run_hook(request(), sock)
    finally:
        srv.close()
    assert out.returncode == 0, out.stderr
    decision = json.loads(out.stdout)["hookSpecificOutput"]
    assert decision["hookEventName"] == "PreToolUse" and decision["permissionDecision"] == "allow"
    assert srv.seen == [{"tool_name": "Bash", "tool_input": {"command": "ls"}, "session_id": "s1"}]


def test_deny_reply_exits_two_with_the_reason_on_stderr(sock):
    srv = serve(sock, {"allow": False, "reason": "Denied: you said no to a request to delete files with rm."})
    try:
        out = run_hook(request(), sock)
    finally:
        srv.close()
    assert out.returncode == 2 and out.stdout == ""
    assert out.stderr.strip() == "Denied: you said no to a request to delete files with rm."


def test_no_socket_exits_two(tmp_path):
    out = run_hook(request(), tmp_path / "missing.sock")
    assert out.returncode == 2 and "not running" in out.stderr and out.stdout == ""


def test_a_stale_socket_file_exits_two(tmp_path):
    stale = tmp_path / "stale.sock"
    s = socket.socket(socket.AF_UNIX)
    s.bind(str(stale))
    s.close()  # file remains, nobody listens
    assert run_hook(request(), stale).returncode == 2


def test_server_that_never_answers_exits_two_within_the_timeout(sock):
    srv = serve(sock, None)
    try:
        start = time.monotonic()
        out = run_hook(request(), sock, timeout=1.0)
        elapsed = time.monotonic() - start
    finally:
        srv.close()
    assert out.returncode == 2 and "in time" in out.stderr and out.stdout == ""
    assert elapsed < 3.0


@pytest.mark.parametrize(
    "reply",
    [
        b"garbage\n",
        b"\n",
        b"[]\n",
        b'{"allow": "yes"}\n',
        b'{"allow": 1}\n',
        b'{"allow": null}\n',
        b"{}\n",
        b'{"permissionDecision": "allow"}\n',
        b'{"allow": true',  # no newline, then close
        b"",
    ],
)
def test_garbage_or_unclear_replies_exit_two(sock, reply):
    srv = serve(sock, reply)
    try:
        out = run_hook(request(), sock)
    finally:
        srv.close()
    assert out.returncode == 2 and out.stdout == ""


@pytest.mark.parametrize("stdin", ["", "   \n", "not json", "[]", "null", "{}", '{"tool_name": "Bash"}', '{"tool_name": 5, "tool_input": {}}', '{"tool_name": "Bash", "tool_input": "ls"}'])
def test_bad_stdin_exits_two_without_asking_hark(sock, stdin):
    srv = serve(sock, {"allow": True, "reason": "x"})
    try:
        out = run_hook(stdin, sock)
    finally:
        srv.close()
    assert out.returncode == 2 and out.stdout == "" and srv.seen == []


def test_bad_arguments_exit_two(sock):
    out = subprocess.run([sys.executable, str(HOOK), "--timeout", "abc"], input=request(), capture_output=True, text=True)
    assert out.returncode == 2 and out.stdout == ""
    out = subprocess.run([sys.executable, str(HOOK), "--timeout"], input=request(), capture_output=True, text=True)
    assert out.returncode == 2


def test_hook_imports_nothing_from_hark():
    code = (
        "import runpy, sys; runpy.run_path(sys.argv[1], run_name='not_main'); "
        "bad = [m for m in sys.modules if m == 'hark' or m.startswith('hark.')]; "
        "sys.exit(1 if bad else 0)"
    )
    out = subprocess.run([sys.executable, "-I", "-c", code, str(HOOK)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr


# --- GateServer end to end --------------------------------------------------


class ScriptedGate:
    """Answers per command; records the order and overlap of checks."""

    def __init__(self, delay: float = 0.0) -> None:
        self.calls: list[ToolCall] = []
        self.active = self.max_active = 0
        self.delay = delay

    async def check(self, call: ToolCall) -> GateDecision:
        self.calls.append(call)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(self.delay)
        finally:
            self.active -= 1
        ok = call.input.get("command") == "ls"
        return GateDecision(ok, "read-only command" if ok else "Denied: no.")


def hook_async(stdin, sock, timeout=5.0):
    return asyncio.to_thread(run_hook, stdin, sock, timeout)


def test_server_round_trip_allow_and_deny(tmp_path):
    async def go():
        gate = ScriptedGate()
        async with GateServer(gate, lambda: "turn-9", tmp_path / "d" / "g.sock") as srv:
            ok = await hook_async(request(command="ls"), srv.path)
            no = await hook_async(request(command="rm x"), srv.path)
        return gate, ok, no

    gate, ok, no = asyncio.run(go())
    assert ok.returncode == 0 and no.returncode == 2 and "Denied" in no.stderr
    assert [c.turn_id for c in gate.calls] == ["turn-9", "turn-9"]
    assert gate.calls[1].input == {"command": "rm x"}


def test_socket_is_private_and_removed_on_shutdown(tmp_path):
    async def go():
        async with GateServer(ScriptedGate(), lambda: "t", tmp_path / "d" / "g.sock") as srv:
            mode = stat.S_IMODE(os.stat(srv.path).st_mode)
            dmode = stat.S_IMODE(os.stat(srv.path.parent).st_mode)
            existed = srv.path.exists()
        return mode, dmode, existed, srv.path.exists()

    mode, dmode, existed, after = asyncio.run(go())
    assert mode == 0o600 and dmode == 0o700 and existed and not after


def test_server_replaces_a_stale_socket_but_refuses_a_live_one(tmp_path):
    path = tmp_path / "g.sock"
    s = socket.socket(socket.AF_UNIX)
    s.bind(str(path))
    s.close()

    async def go():
        async with GateServer(ScriptedGate(), lambda: "t", path):
            with pytest.raises(RuntimeError, match="already listening"):
                await GateServer(ScriptedGate(), lambda: "t", path).start()

    asyncio.run(go())


def test_requests_are_asked_one_at_a_time(tmp_path):
    async def go():
        gate = ScriptedGate(delay=0.15)
        async with GateServer(gate, lambda: "t", tmp_path / "g.sock") as srv:
            outs = await asyncio.gather(*(hook_async(request(command="ls"), srv.path) for _ in range(4)))
        return gate, outs

    gate, outs = asyncio.run(go())
    assert all(o.returncode == 0 for o in outs)
    assert gate.max_active == 1


def test_a_request_whose_hook_died_is_dropped_not_asked(tmp_path):
    async def go():
        gate = ScriptedGate(delay=0.6)
        async with GateServer(gate, lambda: "t", tmp_path / "g.sock") as srv:
            first = asyncio.create_task(hook_async(request(command="ls"), srv.path))
            await asyncio.sleep(0.2)
            # a second hook queues behind the first, then is killed (as Claude would at its timeout)
            r, w = await asyncio.open_unix_connection(str(srv.path))
            w.write(request(command="ls").encode() + b"\n")
            await w.drain()
            await asyncio.sleep(0.1)
            w.close()
            await first
            await asyncio.sleep(0.8)
        return gate

    gate = asyncio.run(go())
    assert len(gate.calls) == 1


def test_a_queued_request_that_waits_too_long_is_denied(tmp_path):
    async def go():
        gate = ScriptedGate(delay=1.5)
        async with GateServer(gate, lambda: "t", tmp_path / "g.sock", request_timeout=0.5) as srv:
            return await asyncio.gather(
                hook_async(request(command="ls"), srv.path),
                hook_async(request(command="ls"), srv.path),
            )

    outs = asyncio.run(go())
    assert [o.returncode for o in outs] == [2, 2]
    assert "ran out of time" in outs[0].stderr


@pytest.mark.parametrize("line", [b"garbage\n", b"[]\n", b'{"tool_name": "Bash"}\n', b"\n"])
def test_server_denies_malformed_requests(tmp_path, line):
    async def go():
        gate = ScriptedGate()
        async with GateServer(gate, lambda: "t", tmp_path / "g.sock") as srv:
            r, w = await asyncio.open_unix_connection(str(srv.path))
            w.write(line)
            await w.drain()
            reply = json.loads(await r.readline())
        return gate, reply

    gate, reply = asyncio.run(go())
    assert reply["allow"] is False and gate.calls == []


def test_a_gate_that_raises_is_denied(tmp_path):
    class Boom:
        async def check(self, call):
            raise RuntimeError("bug")

    async def go():
        async with GateServer(Boom(), lambda: "t", tmp_path / "g.sock") as srv:
            return await hook_async(request(), srv.path)

    out = asyncio.run(go())
    assert out.returncode == 2 and "Denied" in out.stderr


def test_a_turn_id_provider_that_raises_does_not_stop_the_gate(tmp_path):
    def broken():
        raise LookupError

    async def go():
        gate = ScriptedGate()
        async with GateServer(gate, broken, tmp_path / "g.sock") as srv:
            await hook_async(request(command="ls"), srv.path)
        return gate

    assert asyncio.run(go()).calls[0].turn_id == "no-turn"


def test_real_gate_behind_the_real_server_and_hook(tmp_path):
    """Voice yes allows a push; voice no denies; ls is allowed without asking."""
    from tests.test_gate_confirm_and_gate import CONFIG, ScriptedSTT

    async def go():
        bus, tts = InMemoryEventBus(), StubTextToSpeech()
        stt = ScriptedSTT(("yes", 0.2), ("no", 0.2))
        gate = HarkSafetyGate(bus, tts, stt, confirmer=Confirmer(tts, stt, CONFIG))
        async with GateServer(gate, lambda: "t1", tmp_path / "g.sock") as srv:
            ls = await hook_async(request(command="ls"), srv.path)
            yes = await hook_async(request(command="git push"), srv.path)
            no = await hook_async(request(command="rm -rf build"), srv.path)
            write = await hook_async(request("Write", file_path="x", content="y"), srv.path)
        return ls, yes, no, write, tts

    ls, yes, no, write, tts = asyncio.run(go())
    assert (ls.returncode, yes.returncode, no.returncode) == (0, 0, 2)
    assert "you said no" in no.stderr and "delete files with rm" in no.stderr
    assert write.returncode == 2  # no answers left: silence denies
    assert tts.spoken[0] == "Allow: push to a remote with git? Say yes or no."


# --- settings ----------------------------------------------------------------


def test_hook_settings_shape():
    s = hook_settings("/opt/hark/pretool_hook.py", 15)
    (entry,) = s["hooks"]["PreToolUse"]
    assert entry["matcher"] == "*"
    (hook,) = entry["hooks"]
    assert hook == {
        "type": "command",
        "command": "/opt/hark/pretool_hook.py --timeout 14",
        "timeout": 15,
        "onFailure": "block",
    }
    json.dumps(s)


def test_hook_settings_quote_paths_and_default_timeout():
    s = hook_settings("/with space/h.py")
    hook = s["hooks"]["PreToolUse"][0]["hooks"][0]
    assert hook["command"].startswith("'/with space/h.py' --timeout ")
    assert hook["timeout"] == hook_timeout() == 15


def test_hook_timeout_sits_just_above_the_window():
    assert hook_timeout(GateConfig().window_s) == 15
