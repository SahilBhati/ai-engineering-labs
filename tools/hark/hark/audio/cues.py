"""Sound cues (D8): a rising chime when listening starts, a short one when speech ends."""

from __future__ import annotations

import numpy as np


def _tone(freqs: list[float], note_secs: float, sample_rate: int, volume: float = 0.25) -> bytes:
    n = int(note_secs * sample_rate)
    t = np.arange(n) / sample_rate
    fade = np.minimum(1.0, np.minimum(t, t[::-1]) / 0.01)  # 10 ms ramps, no clicks
    notes = [np.sin(2 * np.pi * f * t) * fade for f in freqs]
    return (np.concatenate(notes) * volume * 32767).astype(np.int16).tobytes()


def listening(sample_rate: int) -> bytes:
    return _tone([660.0, 880.0], 0.07, sample_rate)


def got_it(sample_rate: int) -> bytes:
    return _tone([880.0], 0.06, sample_rate, volume=0.18)
