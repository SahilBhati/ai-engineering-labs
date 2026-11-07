"""``GateServer``: the socket between the pre-tool hook and the safety gate (D6).

One JSON line in, one JSON line out (see ``hooks/pretool_hook.py``). Requests
are answered one at a time, because there is one speaker. If the hook goes
away (Claude Code killed it at its timeout) the pending request is dropped
instead of asked, so the user is never asked about a call that is already
blocked.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Any

from hark.ports import SafetyGate, ToolCall

logger = logging.getLogger(__name__)

DEFAULT_SOCKET = Path.home() / ".config" / "hark" / "gate.sock"
MAX_REQUEST_BYTES = 32 * 1024 * 1024  # a Write call carries its whole file


class GateServer:
    def __init__(
        self,
        gate: SafetyGate,
        current_turn_id: Callable[[], str],
        socket_path: Path | str = DEFAULT_SOCKET,
        request_timeout: float = 13.0,
    ) -> None:
        self._gate = gate
        self._turn_id = current_turn_id
        self.path = Path(socket_path)
        self._timeout = request_timeout
        self._lock = asyncio.Lock()  # one confirmation at a time
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        if len(os.fsencode(self.path)) >= 104:  # macOS sun_path limit
            raise ValueError(f"socket path is too long for a Unix socket: {self.path}")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._clear_stale_socket()
        # The directory is private (0700) before the socket appears in it.
        os.chmod(self.path.parent, 0o700)
        self._server = await asyncio.start_unix_server(
            self._handle, path=str(self.path), limit=MAX_REQUEST_BYTES
        )
        os.chmod(self.path, 0o600)

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        self.path.unlink(missing_ok=True)

    async def __aenter__(self) -> GateServer:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    def _clear_stale_socket(self) -> None:
        if not self.path.exists():
            return
        if not stat.S_ISSOCK(self.path.stat().st_mode):
            raise RuntimeError(f"{self.path} exists and is not a socket")
        probe = socket.socket(socket.AF_UNIX)
        try:
            probe.settimeout(1.0)
            probe.connect(str(self.path))
        except OSError:
            self.path.unlink()  # nobody is listening: left over from a crash
        else:
            raise RuntimeError(f"another Hark is already listening on {self.path}")
        finally:
            probe.close()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            reply = await self._answer(reader)
            if reply is not None:
                writer.write(json.dumps(reply).encode() + b"\n")
                await writer.drain()
        except Exception:
            logger.exception("gate server failed on a request")
        finally:
            writer.close()

    async def _answer(self, reader: asyncio.StreamReader) -> dict[str, Any] | None:
        try:
            line = await asyncio.wait_for(reader.readline(), self._timeout)
            request = json.loads(line)
            call = self._to_call(request)
        except (ValueError, TimeoutError, asyncio.LimitOverrunError):
            return deny("Denied: Hark could not read the request.")
        decide = asyncio.ensure_future(self._decide(call))
        hangup = asyncio.ensure_future(reader.read(1))  # EOF = the hook is gone
        try:
            await asyncio.wait({decide, hangup}, timeout=self._timeout, return_when=asyncio.FIRST_COMPLETED)
            if decide.done():
                return decide.result()
            if hangup.done():
                logger.info("hook went away before an answer; dropping the request")
                return None
            return deny("Denied: Hark ran out of time to ask you.")
        finally:
            for task in (decide, hangup):
                task.cancel()
            await asyncio.gather(decide, hangup, return_exceptions=True)

    def _to_call(self, request: object) -> ToolCall:
        if not isinstance(request, dict):
            raise ValueError("request is not an object")
        tool, tool_input = request.get("tool_name"), request.get("tool_input")
        if not isinstance(tool, str) or not isinstance(tool_input, dict):
            raise ValueError("request lacks tool_name or tool_input")
        try:
            turn_id = self._turn_id()
        except Exception:  # noqa: BLE001 — the gate still decides without a turn
            turn_id = "no-turn"
        logger.info("tool call %s from session %s", tool, request.get("session_id"))
        return ToolCall(turn_id=turn_id, tool=tool, input=tool_input)

    async def _decide(self, call: ToolCall) -> dict[str, Any]:
        async with self._lock:
            try:
                decision = await self._gate.check(call)
            except Exception:
                logger.exception("gate failed; denying")
                return deny("Denied: Hark's safety check failed.")
        return {"allow": decision.allowed is True, "reason": decision.reason}


def deny(reason: str) -> dict[str, Any]:
    return {"allow": False, "reason": reason}
