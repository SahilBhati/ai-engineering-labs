"""One warm ``claude -p`` process speaking stream-JSON both ways (D5, LAB-01).

Turn in: a JSON line ``{"type":"user","message":{"role":"user","content":...}}``.
Turn out: events until one of type ``result``. The format is Claude Code's,
so parsing keeps only what Hark needs and ignores every other event.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from pathlib import Path

# Result events carry the whole answer and usage tables; lines get long.
_LINE_LIMIT = 16 * 1024 * 1024


class ProcessDied(Exception):
    """The child exited or its pipe broke before the turn's ``result``."""


@dataclass(frozen=True)
class StreamEvent:
    kind: str  # "init" | "text" | "result"
    text: str = ""  # text delta, or the final answer for "result"
    session_id: str | None = None
    is_error: bool = False


def parse_line(line: str | bytes) -> StreamEvent | None:
    """Turn one stdout line into an event, or None for anything unknown."""
    try:
        data = json.loads(line)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    kind = data.get("type")
    session_id = data.get("session_id")
    if kind == "system" and data.get("subtype") == "init":
        return StreamEvent("init", session_id=session_id)
    if kind == "stream_event":
        event = data.get("event")
        delta = event.get("delta") if isinstance(event, dict) else None
        if (
            isinstance(event, dict)
            and event.get("type") == "content_block_delta"
            and isinstance(delta, dict)
            and delta.get("type") == "text_delta"
        ):
            return StreamEvent("text", text=delta.get("text", ""), session_id=session_id)
        return None
    if kind == "result":
        result = data.get("result")
        return StreamEvent(
            "result",
            text=result if isinstance(result, str) else "",
            session_id=session_id,
            is_error=bool(data.get("is_error")),
        )
    return None


class ClaudeProcess:
    def __init__(
        self,
        argv: Sequence[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self._argv = list(argv)
        self._cwd = cwd
        self._env = env
        self._proc: asyncio.subprocess.Process | None = None

    async def start(self) -> None:
        self._proc = await asyncio.create_subprocess_exec(
            *self._argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,  # an unread pipe would fill and stall the child
            cwd=self._cwd,
            env={**os.environ, **self._env} if self._env else None,
            limit=_LINE_LIMIT,
        )

    @property
    def pid(self) -> int | None:
        return self._proc.pid if self._proc else None

    @property
    def alive(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def send(self, text: str) -> None:
        if not self.alive:
            raise ProcessDied("process is not running")
        line = json.dumps({"type": "user", "message": {"role": "user", "content": text}})
        try:
            self._proc.stdin.write(line.encode() + b"\n")
            await self._proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError) as exc:
            raise ProcessDied("pipe broke while writing the turn") from exc

    async def events(self) -> AsyncIterator[StreamEvent]:
        """Yield parsed events up to and including ``result``."""
        if self._proc is None:
            raise ProcessDied("process was never started")
        while True:
            line = await self._proc.stdout.readline()
            if not line:
                raise ProcessDied("process exited before the result")
            event = parse_line(line)
            if event is None:
                continue
            yield event
            if event.kind == "result":
                return

    async def stop(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        if proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        await proc.wait()
