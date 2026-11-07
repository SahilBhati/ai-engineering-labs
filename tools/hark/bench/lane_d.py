"""Lane D lab number: latency the gate adds to one allowed tool call.

    uv run python bench/lane_d.py [--calls 50]

Spawns the real hook script the way Claude Code does (executable, shebang) against
a real GateServer + HarkSafetyGate, for an ALLOW command ("ls"), and reports p50
and p95 of the whole hook run. Also times a bare interpreter start, so the cost of
the socket round trip can be told apart from Python's own start-up.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from hark.gate.gate import HarkSafetyGate
from hark.gate.server import GateServer
from hark.stubs import InMemoryEventBus, StubSpeechToText, StubTextToSpeech

HOOK = Path(__file__).parent.parent / "hark" / "hooks" / "pretool_hook.py"
REQUEST = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}, "session_id": "bench"})


def run(argv: list[str], stdin: str = "") -> float:
    start = time.perf_counter()
    subprocess.run(argv, input=stdin, capture_output=True, text=True, check=False)
    return (time.perf_counter() - start) * 1000


def summary(name: str, ms: list[float]) -> str:
    ms = sorted(ms)
    p95 = ms[min(len(ms) - 1, round(0.95 * len(ms)) - 1)]
    return f"{name:<28} p50 {statistics.median(ms):6.1f} ms   p95 {p95:6.1f} ms   n={len(ms)}"


async def main(calls: int) -> None:
    with tempfile.TemporaryDirectory(prefix="hk", dir="/tmp") as d:
        bus, tts, stt = InMemoryEventBus(), StubTextToSpeech(), StubSpeechToText([])
        gate = HarkSafetyGate(bus, tts, stt)
        async with GateServer(gate, lambda: "bench", Path(d) / "g.sock") as srv:
            hook = [str(HOOK), "--socket", str(srv.path), "--timeout", "5"]
            await asyncio.to_thread(run, hook, REQUEST)  # warm the file cache
            with_gate = [await asyncio.to_thread(run, hook, REQUEST) for _ in range(calls)]
            bare = [await asyncio.to_thread(run, ["/usr/bin/env", "python3", "-c", "pass"]) for _ in range(calls)]
    print(summary("hook + gate (allowed call)", with_gate))
    print(summary("bare python3 start-up", bare))
    print(f"python: {sys.version.split()[0]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--calls", type=int, default=50)
    asyncio.run(main(parser.parse_args().calls))
