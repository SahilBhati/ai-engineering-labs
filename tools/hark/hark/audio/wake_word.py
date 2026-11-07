"""WakeWord adapter: openWakeWord on the shared mic (D2)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol

import numpy as np

from hark.audio import cues
from hark.audio.io import AudioIO
from hark.ports import Wake

CHUNK_SAMPLES = 1280  # openWakeWord scores 80 ms of 16 kHz audio at a time


class Scorer(Protocol):
    """The slice of ``openwakeword.Model`` this adapter uses (fakeable in tests)."""

    def predict(self, x: np.ndarray) -> dict[str, float]: ...

    def reset(self) -> None: ...


def load_openwakeword(model: str) -> tuple[Scorer, str]:
    """Load a built-in model by name (``hey_jarvis``) or an ``.onnx`` file by path.

    Returns the scorer and the key its scores come back under.
    """
    from openwakeword.model import Model
    from openwakeword.utils import download_models

    if Path(model).suffix:  # a file path: a custom phrase (R1)
        key = Path(model).stem
    else:
        key = model
        download_models([model])  # no-op once the files are on disk
    return Model(wakeword_models=[model], inference_framework="onnx"), key


class OpenWakeWord:
    """Strategy (D2): the detector and its model file come from config."""

    def __init__(
        self,
        io: AudioIO,
        scorer: Scorer,
        key: str,
        *,
        phrase: str | None = None,
        threshold: float = 0.5,
        cue: bool = True,
    ) -> None:
        self._io = io
        self._scorer = scorer
        self._key = key
        self.phrase = phrase or key.split("_v")[0].replace("_", " ")
        self.threshold = threshold
        self._cue = cue

    async def wait(self) -> Wake:
        self._scorer.reset()  # don't fire on audio from before this wait
        pending = np.empty(0, dtype=np.int16)
        async with self._io.frames() as frames:
            while True:
                pending = np.concatenate([pending, np.frombuffer(await frames.get(), np.int16)])
                while pending.size >= CHUNK_SAMPLES:
                    chunk, pending = pending[:CHUNK_SAMPLES], pending[CHUNK_SAMPLES:]
                    score = (await asyncio.to_thread(self._scorer.predict, chunk))[self._key]
                    if score >= self.threshold:
                        self._scorer.reset()
                        if self._cue:  # D8: rising chime = "listening"
                            rate = self._io.output_sample_rate
                            await self._io.play(cues.listening(rate), rate)
                        return Wake(phrase=self.phrase, score=float(score))
