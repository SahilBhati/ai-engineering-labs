"""Real ``claude``, allow-all hook: two turns, one process, warm first token.

    uv run pytest -m live -s
"""

from __future__ import annotations

import asyncio
import json
import stat
import time

import pytest

from hark.brain import ClaudeBrain
from hark.brain.process import ClaudeProcess
from hark.ports import BrainRequest

pytestmark = pytest.mark.live

HOOK = """#!/bin/bash
cat > /dev/null
exit 0
"""


def test_two_turns_same_pid_and_warm_second_turn(tmp_path):
    hook = tmp_path / "hook.sh"
    hook.write_text(HOOK)
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": str(hook),
                                    "timeout": 10,
                                    "onFailure": "block",
                                }
                            ],
                        }
                    ]
                }
            }
        )
    )

    async def go():
        brain = ClaudeBrain(settings, cwd=tmp_path)
        proc = ClaudeProcess(brain._argv, cwd=tmp_path)  # same flags, timed per event
        await proc.start()
        firsts: list[float] = []
        try:
            for _ in range(2):
                started = time.monotonic()
                first = None
                await proc.send("Reply with only the word: ok")
                async for event in proc.events():
                    if event.kind == "text" and first is None:
                        first = time.monotonic() - started
                firsts.append(first)
            pid = proc.pid
        finally:
            await proc.stop()
        reply = None
        try:
            reply = await brain.ask(BrainRequest("t", "Reply with only the word: ok"))
        finally:
            await brain.aclose()
        return firsts, pid, reply

    firsts, pid, reply = asyncio.run(go())
    print(f"\nfirst token per turn: {firsts}  pid: {pid}  brain reply: {reply}")
    assert firsts[1] < 1.5
    assert reply.spoken.strip()
