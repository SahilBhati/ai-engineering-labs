"""Lane E: the real bus, the turn log, notifications and the event socket."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

import pytest
from test_fake_turn import build

from hark.bus import AsyncEventBus, EventStreamServer
from hark.events import Answered, Event, StageTimed, Transcribed, TurnEnded, TurnStarted
from hark.ports import EventBus
from hark.sinks import Notifier, TurnLog


def test_bus_satisfies_port():
    assert isinstance(AsyncEventBus(), EventBus)


def test_fake_turn_with_real_bus_and_log(tmp_path):
    runner, _, _, _ = build(["Open labs"])
    bus = AsyncEventBus()
    log = TurnLog(tmp_path / "turns.jsonl")
    seen: list[Event] = []

    async def collect(e: Event) -> None:
        seen.append(e)

    bus.subscribe(log.handle)
    bus.subscribe(collect)
    runner.bus = bus

    async def go() -> None:
        await runner.run_once()
        await bus.close()

    asyncio.run(go())
    assert type(seen[0]).__name__ == "TurnStarted"
    assert type(seen[-1]).__name__ == "TurnEnded"
    lines = [json.loads(x) for x in (tmp_path / "turns.jsonl").read_text().splitlines()]
    assert len(lines) == len(seen) + 1
    summary = lines[-1]
    assert summary["type"] == "TurnSummary" and summary["route"] == "fast"
    assert set(summary["stages"]) == {"listen", "route", "action", "speak"}


def test_failing_and_hanging_subscribers_do_not_break_or_stall():
    bus = AsyncEventBus(handler_timeout=0.05)
    got: list[str] = []

    async def boom(e: Event) -> None:
        raise RuntimeError("bad subscriber")

    async def hang(e: Event) -> None:
        await asyncio.sleep(10)

    async def good(e: Event) -> None:
        got.append(type(e).__name__)

    for h in (boom, hang, good):
        bus.subscribe(h)

    async def go() -> float:
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        await bus.publish(TurnStarted(turn_id="t", wake_phrase="hey"))
        await bus.publish(TurnEnded(turn_id="t", outcome="answered"))
        elapsed = loop.time() - t0
        await bus.close()
        return elapsed

    elapsed = asyncio.run(go())
    assert elapsed < 0.05  # publish never waited on a subscriber
    assert got == ["TurnStarted", "TurnEnded"]


def test_summary_has_every_stage_and_r6_latency(tmp_path):
    log = TurnLog(tmp_path / "t.jsonl")
    events = [
        TurnStarted(turn_id="t", wake_phrase="hey", ts=0.0),
        StageTimed(turn_id="t", stage="listen", started=0.0, ended=2.0),
        Transcribed(turn_id="t", text="hi", speech_ended_at=2.0, ts=2.1),
        StageTimed(turn_id="t", stage="route", started=2.1, ended=2.11),
        StageTimed(turn_id="t", stage="speak", started=2.6, ended=3.0),
        TurnEnded(turn_id="t", outcome="answered", ts=3.0),
    ]

    async def go() -> None:
        for e in events:
            await log.handle(e)

    asyncio.run(go())
    summary = json.loads((tmp_path / "t.jsonl").read_text().splitlines()[-1])
    assert summary["stages"] == {"listen": 2.0, "route": 0.01, "speak": 0.4}
    assert summary["r6_latency"] == pytest.approx(0.6)


def test_notifier_only_for_answers_with_detail():
    calls: list[list[str]] = []

    async def fake_run(argv: list[str]) -> None:
        calls.append(argv)

    n = Notifier(run=fake_run)

    async def go() -> None:
        await n.handle(Answered(turn_id="t", spoken="Done."))
        await n.handle(Answered(turn_id="t", spoken="Done.", detail="main -> origin/main"))
        await n.handle(TurnEnded(turn_id="t", outcome="answered"))

    asyncio.run(go())
    assert len(calls) == 1
    assert calls[0][0] == "osascript" and calls[0][-1] == "main -> origin/main"


@pytest.fixture
def short_dir():
    """macOS caps a Unix socket path at 104 bytes, and pytest's tmp_path is longer."""
    with tempfile.TemporaryDirectory(prefix="hk", dir="/tmp") as d:
        yield Path(d)


def test_socket_client_receives_events(short_dir):
    path = short_dir / "e.sock"

    async def go() -> list[dict]:
        server = EventStreamServer(path)
        await server.start()
        bus = AsyncEventBus()
        bus.subscribe(server.handle)
        reader, writer = await asyncio.open_unix_connection(str(path))
        await asyncio.sleep(0.05)  # let the server register the client
        await bus.publish(TurnStarted(turn_id="t", wake_phrase="hey"))
        await bus.publish(TurnEnded(turn_id="t", outcome="answered"))
        got = [json.loads(await asyncio.wait_for(reader.readline(), 2)) for _ in range(2)]
        writer.close()
        await bus.close()
        await server.close()
        return got

    got = asyncio.run(go())
    assert [g["type"] for g in got] == ["TurnStarted", "TurnEnded"]
    assert not path.exists()
