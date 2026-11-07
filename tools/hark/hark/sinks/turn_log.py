"""``TurnLog``: append every event as a JSON line, plus a summary per turn.

On ``TurnEnded`` it writes one ``{"type": "TurnSummary", ...}`` line: the
route, each stage's duration, and R6 latency, the time from the end of
speech to the moment the answer starts to be spoken (the ``speak`` stage's
start). Everything uses the one monotonic clock from ``hark.events``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hark.events import Event, Routed, StageTimed, Transcribed, TurnEnded

DEFAULT_TURN_LOG = Path.home() / "Library" / "Logs" / "hark" / "turns.jsonl"


class TurnLog:
    def __init__(self, path: Path | str = DEFAULT_TURN_LOG) -> None:
        self.path = Path(path)
        self._turns: dict[str, dict[str, Any]] = {}

    async def handle(self, event: Event) -> None:
        turn = self._turns.setdefault(event.turn_id, {"stages": {}})
        lines = [event.to_dict()]
        match event:
            case Transcribed():
                turn["speech_ended_at"] = event.speech_ended_at
            case Routed():
                turn["route"] = event.route
                turn["action"] = event.action
            case StageTimed():
                turn["stages"][event.stage] = round(event.duration, 4)
                if event.stage == "speak":
                    turn["spoken_at"] = event.started
            case TurnEnded():
                lines.append(self._summary(event, self._turns.pop(event.turn_id)))
        self._append(lines)

    def _summary(self, ended: TurnEnded, turn: dict[str, Any]) -> dict[str, Any]:
        latency = None
        if "speech_ended_at" in turn and "spoken_at" in turn:
            latency = round(turn["spoken_at"] - turn["speech_ended_at"], 4)
        return {
            "type": "TurnSummary",
            "turn_id": ended.turn_id,
            "outcome": ended.outcome,
            "route": turn.get("route"),
            "action": turn.get("action"),
            "stages": turn["stages"],
            "r6_latency": latency,
        }

    def _append(self, lines: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write("".join(json.dumps(line) + "\n" for line in lines))
