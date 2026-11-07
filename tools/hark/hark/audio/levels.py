"""Audio level and silence-hallucination checks. Pure functions, no I/O."""

from __future__ import annotations

import re

import numpy as np

# What Whisper says when it hears silence or noise (F6). Compared after
# normalising: lower case, punctuation dropped, repeats collapsed.
SILENCE_HALLUCINATIONS = frozenset(
    {
        "thank you",
        "thanks",
        "thanks for watching",
        "thank you for watching",
        "thank you so much for watching",
        "please subscribe",
        "subscribe",
        "you",
        "bye",
        "bye bye",
        "okay",
        "oh",
        "so",
        "hmm",
    }
)

# Markers whisper.cpp emits for non-speech; never a real utterance.
_NON_SPEECH = re.compile(r"^\s*([\[(][^\])]*[\])]\s*)+$")


def rms(pcm: bytes) -> float:
    """Root-mean-square level of 16-bit mono PCM, 0.0 (silence) to 1.0 (full scale)."""
    samples = np.frombuffer(pcm[: len(pcm) - len(pcm) % 2], dtype=np.int16)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean((samples.astype(np.float64) / 32768.0) ** 2)))


def normalise(text: str) -> str:
    words = re.sub(r"[^\w\s']", " ", text.lower()).split()
    phrase = " ".join(words)
    # "thank you thank you" → "thank you": collapse a phrase repeated back to back.
    for size in range(1, len(words) // 2 + 1):
        unit = words[:size]
        if len(words) % size == 0 and unit * (len(words) // size) == words:
            return " ".join(unit)
    return phrase


def is_non_speech(text: str) -> bool:
    """Empty, punctuation only, or a marker such as ``[BLANK_AUDIO]``."""
    return not normalise(text) or bool(_NON_SPEECH.match(text))


def is_silence_hallucination(text: str, energy: float, min_energy: float) -> bool:
    """A known silence phrase on quiet audio: Whisper made it up (F6, backlog H3).

    Loud audio keeps the phrase: a real "thank you" is a real utterance.
    """
    return energy < min_energy and normalise(text) in SILENCE_HALLUCINATIONS
