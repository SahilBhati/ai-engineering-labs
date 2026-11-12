"""ClaudeBrain: the Brain port over one supervised Claude Code process (D5).

Pattern: Adapter (``ask`` over a stream-JSON child), with a small
supervisor: lazy start, restart after a crash or timeout, rollover between
turns. Safety is not enforced here; the pre-tool hook in the settings file
(lane D) is, and this class never builds hook JSON.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from hark.brain.process import ClaudeProcess, ProcessDied
from hark.ports import BrainReply, BrainRequest

MARKER = "DETAIL:"
_MARKER_RE = re.compile(r"^[ \t]*DETAIL:[ \t]*", re.MULTILINE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

SYSTEM_PROMPT = (
    "You are the brain of a voice assistant; your answer is read aloud. "
    "Answer in one or two short spoken sentences with no markdown. "
    "If more detail is useful, put a line containing only 'DETAIL:' after "
    "the spoken part, then the long form (it is shown on screen, not spoken)."
)

LOST = "Sorry, I lost that one. Try again."
TOO_SLOW = "That took too long."
FAILED = "Sorry, that didn't work."


class BrainUnavailable(Exception):
    """The Claude process could not be started after repeated tries."""


def split_reply(text: str, cap: int = 240) -> BrainReply:
    """Split on the ``DETAIL:`` marker; cap what is spoken.

    No marker: speak the first sentences that fit the cap, keep the whole
    text as detail. Marker present but the spoken part is over the cap: the
    spoken part is cut the same way and the full text becomes the detail.
    """
    text = text.strip()
    match = _MARKER_RE.search(text)
    if match:
        spoken = text[: match.start()].strip()
        detail = text[match.end() :].strip() or None
        if not spoken:  # marker first: speak the start of the detail
            spoken, detail = detail or "", None
        if len(spoken) <= cap:
            return BrainReply(spoken=spoken, detail=detail)
        full = f"{spoken}\n\n{detail}" if detail else spoken
        return BrainReply(spoken=_first_sentences(spoken, cap), detail=full)
    spoken = _first_sentences(text, cap)
    return BrainReply(spoken=spoken, detail=text if spoken != text else None)


def _first_sentences(text: str, cap: int) -> str:
    kept = ""
    for sentence in _SENTENCE_RE.split(text):
        candidate = f"{kept} {sentence}".strip()
        if len(candidate) > cap:
            break
        kept = candidate
    if kept:
        return kept
    cut = text[:cap].rsplit(" ", 1)[0] if " " in text[:cap] else text[:cap]
    return cut.rstrip()


class ClaudeBrain:
    def __init__(
        self,
        settings_path: Path,
        *,
        model: str | None = None,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        command: Sequence[str] = ("claude",),
        spoken_cap: int = 240,
        turn_timeout: float = 120.0,
        max_turns: int = 30,
        max_idle: float = 30 * 60,
        max_start_failures: int = 5,
        backoff: Sequence[float] = (1, 2, 4, 8, 16, 30),
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], object] = asyncio.sleep,
    ) -> None:
        self._argv = [
            *command,
            "-p",
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
            "--settings", str(settings_path),
            "--append-system-prompt", SYSTEM_PROMPT,
        ]  # fmt: skip
        if model:
            self._argv += ["--model", model]
        self._cwd = cwd if cwd is not None else Path.home()
        self._env = dict(env) if env else None  # added to the inherited environment
        self._spoken_cap = spoken_cap
        self._turn_timeout = turn_timeout
        self._max_turns = max_turns
        self._max_idle = max_idle
        self._max_start_failures = max_start_failures
        self._backoff = tuple(backoff)
        self._clock = clock
        self._sleep = sleep
        self._proc: ClaudeProcess | None = None
        self._turns = 0
        self._last_turn_end = 0.0
        self._lock = asyncio.Lock()

    async def ask(self, request: BrainRequest) -> BrainReply:
        async with self._lock:  # one turn at a time through one process
            proc = await self._ready()
            try:
                async with asyncio.timeout(self._turn_timeout):
                    await proc.send(request.text)
                    answer = await self._collect(proc)
            except ProcessDied:
                await self._drop()
                return BrainReply(spoken=LOST)
            except TimeoutError:
                await self._drop()
                return BrainReply(spoken=TOO_SLOW)
            self._turns += 1
            self._last_turn_end = self._clock()
            text, is_error = answer
            if is_error or not text.strip():
                return BrainReply(spoken=FAILED, detail=text.strip() or None)
            return split_reply(text, self._spoken_cap)

    async def aclose(self) -> None:
        await self._drop()

    async def _collect(self, proc: ClaudeProcess) -> tuple[str, bool]:
        streamed: list[str] = []
        async for event in proc.events():
            if event.kind == "text":
                streamed.append(event.text)
            elif event.kind == "result":
                return (event.text or "".join(streamed)), event.is_error
        raise ProcessDied("no result")  # events() raises first; kept for safety

    async def _ready(self) -> ClaudeProcess:
        """A live process, started lazily, rolled over between turns."""
        if self._proc is not None and not self._proc.alive:
            await self._drop()
        if self._proc is not None and self._due_for_rollover():
            await self._drop()
        if self._proc is None:
            self._proc = await self._start()
            self._turns = 0
        return self._proc

    def _due_for_rollover(self) -> bool:
        idle = self._clock() - self._last_turn_end
        return self._turns >= self._max_turns or (self._turns > 0 and idle >= self._max_idle)

    async def _start(self) -> ClaudeProcess:
        failures = 0
        while True:
            proc = ClaudeProcess(self._argv, cwd=self._cwd, env=self._env)
            try:
                await proc.start()
                return proc
            except OSError as exc:
                failures += 1
                if failures >= self._max_start_failures:
                    raise BrainUnavailable(
                        f"could not start {self._argv[0]!r} after {failures} tries: {exc}"
                    ) from exc
                delay = self._backoff[min(failures - 1, len(self._backoff) - 1)]
                await self._sleep(delay)

    async def _drop(self) -> None:
        proc, self._proc = self._proc, None
        if proc is not None:
            await proc.stop()
