"""Speech-to-text port: one spoken utterance in, text out (R7, D3).

Capture, voice activity detection and transcription all live behind this
port, inside the audio boundary (D1). Hark core never sees audio frames.
The safety gate uses the same ``listen`` to hear a spoken yes (R5).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Transcript:
    text: str
    speech_ended_at: float  # time.monotonic() when the speaker stopped
    energy: float | None = None  # audio level; the gate rejects quiet "yes" (F6)


@runtime_checkable
class SpeechToText(Protocol):
    """Adapter over a local speech-to-text engine."""

    async def listen(self, timeout: float | None = None) -> Transcript | None:
        """Capture one utterance and transcribe it.

        Returns None on silence or timeout — callers treat that as "no".
        """
        ...
