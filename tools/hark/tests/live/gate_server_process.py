"""A real GateServer + HarkSafetyGate in its own process, so a test can kill it.

    python gate_server_process.py SOCKET EVENTS_FILE '[["yes", 0.2], null, ...]'

The JSON list is the spoken answers, in order (null is silence). Events are
appended to EVENTS_FILE as JSON lines.
"""

import asyncio
import json
import sys

from hark.gate.config import GateConfig
from hark.gate.confirm import Confirmer
from hark.gate.gate import HarkSafetyGate
from hark.gate.server import GateServer
from hark.ports import Transcript
from hark.stubs import InMemoryEventBus, StubTextToSpeech


class Scripted:
    def __init__(self, answers):
        self.answers = list(answers)

    async def listen(self, timeout=None):
        item = self.answers.pop(0) if self.answers else None
        return None if item is None else Transcript(item[0], 0.0, item[1])


async def main(sock, events_path, answers):
    bus, tts, stt = InMemoryEventBus(), StubTextToSpeech(), Scripted(answers)

    async def log(event):
        with open(events_path, "a") as f:
            f.write(json.dumps(event.to_dict()) + "\n")

    bus.subscribe(log)
    gate = HarkSafetyGate(bus, tts, stt, confirmer=Confirmer(tts, stt, GateConfig(window_s=6.0)))
    async with GateServer(gate, lambda: "live-turn", sock):
        print("ready", flush=True)
        await asyncio.Event().wait()


asyncio.run(main(sys.argv[1], sys.argv[2], json.loads(sys.argv[3])))
