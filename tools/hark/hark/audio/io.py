"""What the adapters need from the audio engine (pattern: Dependency Inversion).

The adapters depend on this protocol, not on Pipecat, so they are tested with
a fake engine and no sound card.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Utterance:
    pcm: bytes  # 16-bit mono, includes pre-roll and the trailing silence VAD waited for
    voiced: bytes  # the same audio trimmed to the speech itself, for the level check
    sample_rate: int
    ended_at: float  # time.monotonic() when VAD decided speech ended


class AudioIO(Protocol):
    input_sample_rate: int
    output_sample_rate: int

    def frames(self) -> AbstractAsyncContextManager[asyncio.Queue[bytes]]:
        """Subscribe to raw mic audio (16-bit mono) for as long as the context is open."""
        ...

    async def next_utterance(
        self, start_timeout: float | None, max_secs: float
    ) -> Utterance | None:
        """One utterance bounded by VAD, or None if speech doesn't start in time."""
        ...

    async def play(self, audio: bytes | AsyncIterable[bytes], sample_rate: int) -> None:
        """Play 16-bit mono PCM; return when playback ends."""
        ...
