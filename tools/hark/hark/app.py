"""The Hark app: every lane wired together, one turn after another.

    python -m hark.app

Pattern: Composition Root. This is the one place that picks concrete
adapters for the ports; nothing else imports across lanes.

Start order matters. The two sockets come first, because each refuses to
start if another Hark is already listening: a second instance fails there,
before it touches the mic or starts a ``claude``. The speech servers are
checked next, so a missing one fails loudly by name instead of mid-turn.

Shutdown (SIGTERM or SIGINT): stop the loop, close the gate socket (the hook
then blocks everything), stop the Claude child, stop audio, flush the bus,
close the event socket. No ``claude`` child or socket file is left behind.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import socket
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from hark.actions.open_resource import DEFAULT_CONFIG as ACTIONS_CONFIG
from hark.actions.open_resource import load_resources
from hark.brain.claude import BrainUnavailable, ClaudeBrain
from hark.bus.bus import AsyncEventBus
from hark.bus.stream import DEFAULT_EVENT_SOCKET, EventStreamServer
from hark.gate.config import GateConfig
from hark.gate.confirm import Confirmer
from hark.gate.gate import HarkSafetyGate
from hark.gate.server import DEFAULT_SOCKET as GATE_SOCKET
from hark.gate.server import GateServer
from hark.gate.settings import hook_settings, hook_timeout
from hark.ports import (
    ActionRegistry,
    Brain,
    BrainReply,
    BrainRequest,
    SpeechToText,
    TextToSpeech,
    WakeWord,
)
from hark.router.rules import RulesRouter
from hark.sinks.notify import Notifier
from hark.sinks.turn_log import DEFAULT_TURN_LOG, TurnLog
from hark.turn import TurnRunner

if TYPE_CHECKING:
    from hark.audio import Audio, AudioConfig

logger = logging.getLogger("hark.app")

CONFIG_DIR = Path.home() / ".config" / "hark"
HOOK = Path(__file__).parent / "hooks" / "pretool_hook.py"
NO_BRAIN = "I can't reach Claude right now. Fixed commands still work."


class ServerDown(Exception):
    """A local speech server (whisper or kokoro) is not listening."""


@dataclass(frozen=True)
class Paths:
    gate_socket: Path = GATE_SOCKET
    event_socket: Path = DEFAULT_EVENT_SOCKET
    turn_log: Path = DEFAULT_TURN_LOG
    actions: Path = ACTIONS_CONFIG
    claude_settings: Path = CONFIG_DIR / "claude-settings.json"
    audio_config: Path = CONFIG_DIR / "audio.toml"
    gate_config: Path = CONFIG_DIR / "gate.toml"


class GuardedBrain:
    """Decorator over a ``Brain``: an unreachable ``claude`` becomes a spoken
    reply, so the loop keeps serving fixed commands."""

    def __init__(self, brain: Brain) -> None:
        self._brain = brain

    async def ask(self, request: BrainRequest) -> BrainReply:
        try:
            return await self._brain.ask(request)
        except BrainUnavailable as exc:
            logger.error("brain unavailable: %s", exc)
            return BrainReply(spoken=NO_BRAIN, detail=str(exc))


def write_claude_settings(path: Path, hook: Path = HOOK, timeout: int | None = None) -> Path:
    """Regenerate the ``--settings`` file at every start, so it never drifts from the code."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(hook_settings(hook, timeout), indent=2) + "\n")
    return path


def check_servers(urls: Mapping[str, str], wait: float = 30.0, step: float = 1.0) -> None:
    """Fail with the name of any speech server that isn't listening.

    Waits up to ``wait`` seconds first: at login the speech servers may
    start after Hark does.
    """
    deadline = time.monotonic() + wait
    while True:
        down = [name for name, url in urls.items() if not _listening(url)]
        if not down:
            return
        if time.monotonic() >= deadline:
            detail = ", ".join(f"{name} ({urls[name]})" for name in down)
            raise ServerDown(f"speech server not reachable: {detail}")
        time.sleep(step)


def _listening(url: str) -> bool:
    parts = urlsplit(url)
    try:
        with socket.create_connection((parts.hostname, parts.port or 80), timeout=1.0):
            return True
    except OSError:
        return False


@dataclass
class App:
    """Everything built and owned in one place; ``run`` loops turns until stopped."""

    wake: WakeWord
    stt: SpeechToText
    tts: TextToSpeech
    actions: ActionRegistry
    brain: ClaudeBrain | Brain
    paths: Paths = field(default_factory=Paths)
    gate_config: GateConfig = field(default_factory=GateConfig)
    audio: Audio | None = None  # None in tests: the adapters are fakes with nothing to start

    def __post_init__(self) -> None:
        self.bus = AsyncEventBus()
        self.turn_log = TurnLog(self.paths.turn_log)
        self.stream = EventStreamServer(self.paths.event_socket)
        self.notifier = Notifier()
        for handler in (self.turn_log.handle, self.notifier.handle, self.stream.handle):
            self.bus.subscribe(handler)
        self.gate = HarkSafetyGate(
            self.bus, self.tts, self.stt, confirmer=Confirmer(self.tts, self.stt, self.gate_config)
        )
        self.runner = TurnRunner(
            wake=self.wake,
            stt=self.stt,
            router=RulesRouter(self.actions),
            actions=self.actions,
            brain=GuardedBrain(self.brain),
            tts=self.tts,
            bus=self.bus,
        )
        self.gate_server = GateServer(
            self.gate,
            current_turn_id=lambda: self.runner.current_turn or "no-turn",
            socket_path=self.paths.gate_socket,
            request_timeout=hook_timeout(self.gate_config.window_s) - 2,
        )
        self._started: list[str] = []

    async def start(self) -> None:
        # Sockets first: each refuses if another Hark is listening (single instance).
        await self.gate_server.start()
        self._started.append("gate")
        await self.stream.start()
        self._started.append("stream")
        if self.audio is not None:
            await self.audio.start()
            self._started.append("audio")
        logger.info("hark started: gate %s, events %s", self.paths.gate_socket, self.paths.event_socket)

    async def run(self, turns: int | None = None) -> None:
        """Run turns until cancelled (or ``turns`` of them, for tests)."""
        done = 0
        while turns is None or done < turns:
            try:
                turn_id = await self.runner.run_once()
                logger.info("turn %s done", turn_id)
            except asyncio.CancelledError:
                raise
            except Exception:  # one broken turn must not stop the service
                logger.exception("turn failed")
            done += 1

    async def stop(self) -> None:
        """Close in the reverse order; each step runs even if one before it failed."""
        steps = [
            ("gate", self.gate_server.close),  # from here the hook blocks every call
            ("brain", getattr(self.brain, "aclose", None)),
            ("audio", self.audio.stop if self.audio else None),
            ("bus", self.bus.close),  # flushes the turn log and the stream
            ("stream", self.stream.close),
        ]
        for name, close in steps:
            if close is None or (name in ("gate", "stream", "audio") and name not in self._started):
                continue
            try:
                await close()
            except Exception:
                logger.exception("closing %s failed", name)
        self._started.clear()
        logger.info("hark stopped")


def build(paths: Paths | None = None) -> App:
    """The real app: real audio, router, resources, gate and Claude."""
    from hark.audio import AudioConfig, build_audio

    paths = paths or Paths()
    audio_config = (
        AudioConfig.from_toml(paths.audio_config) if paths.audio_config.exists() else AudioConfig()
    )
    gate_config = GateConfig.load(paths.gate_config)
    check_servers({"whisper": audio_config.whisper_url, "kokoro": audio_config.kokoro_url})
    audio = build_audio(audio_config)
    settings = write_claude_settings(paths.claude_settings, timeout=hook_timeout(gate_config.window_s))
    brain = ClaudeBrain(
        settings,
        model=os.environ.get("HARK_MODEL") or None,
        env={"HARK_GATE_SOCKET": str(paths.gate_socket)},
    )
    return App(
        wake=audio.wake_word,
        stt=audio.speech_to_text,
        tts=audio.text_to_speech,
        actions=load_resources(paths.actions),
        brain=brain,
        paths=paths,
        gate_config=gate_config,
        audio=audio,
    )


async def serve(app: App, signals: Sequence[int] = (signal.SIGTERM, signal.SIGINT)) -> None:
    """Start, loop turns until a signal, then stop cleanly."""
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    assert task is not None
    for sig in signals:
        loop.add_signal_handler(sig, task.cancel)
    try:
        await app.start()
        await app.run()
    except asyncio.CancelledError:
        logger.info("stop requested")
    finally:
        for sig in signals:
            loop.remove_signal_handler(sig)
        await app.stop()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        app = build()
    except (ServerDown, FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        return 1
    try:
        asyncio.run(serve(app))
    except RuntimeError as exc:  # "another Hark is already listening/streaming"
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
