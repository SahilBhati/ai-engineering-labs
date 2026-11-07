"""Audio settings: servers, wake model, vocabulary, thresholds."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

# Project and tool names Whisper mishears without a hint (F1: "Claude" → "cloud").
DEFAULT_VOCABULARY = (
    "Claude",
    "Claude Code",
    "Hark",
    "Pipecat",
    "Kokoro",
    "Whisper",
    "openWakeWord",
    "labs",
    "ai-vault",
    "ai-engineering-labs",
    "repo",
    "git push",
)


@dataclass(frozen=True)
class AudioConfig:
    # Servers borrowed from VoiceMode until Hark owns its own (backlog H4).
    whisper_url: str = "http://127.0.0.1:2022/v1/audio/transcriptions"
    kokoro_url: str = "http://127.0.0.1:8880/v1/audio/speech"
    voice: str = "af_sky"

    # Wake word (D2): a built-in openWakeWord name or a path to an .onnx model.
    wake_model: str = "hey_jarvis"
    wake_threshold: float = 0.5

    # Speech-to-text (D3, F1).
    vocabulary: tuple[str, ...] = DEFAULT_VOCABULARY
    language: str = "en"

    # Voice activity detection (F3: don't cut turns short).
    vad_start_secs: float = 0.2
    vad_stop_secs: float = 0.8
    pre_roll_secs: float = 0.5  # audio kept from before VAD fired, so the first syllable survives
    max_utterance_secs: float = 30.0

    # Below this RMS (0..1 of int16 full scale) an utterance is "quiet": known
    # silence hallucinations are dropped (F6, backlog H3).
    min_energy: float = 0.02  # room noise measured 0.0096 (2026-11-07); calibrate on real speech

    # Sound cues on wake and end of speech (D8).
    cues: bool = True

    input_sample_rate: int = 16000  # openWakeWord, Silero and Whisper all want 16 kHz
    output_sample_rate: int = 24000  # Kokoro's native rate

    @classmethod
    def from_toml(cls, path: str | Path) -> AudioConfig:
        """Read the ``[audio]`` table; unknown keys are an error, missing keys keep defaults."""
        table = tomllib.loads(Path(path).read_text()).get("audio", {})
        known = {f.name for f in fields(cls)}
        unknown = set(table) - known
        if unknown:
            raise ValueError(f"unknown [audio] keys: {sorted(unknown)}")
        if "vocabulary" in table:
            table["vocabulary"] = tuple(table["vocabulary"])
        return cls(**table)

    @property
    def vocabulary_prompt(self) -> str:
        return ", ".join(self.vocabulary) + "." if self.vocabulary else ""


__all__ = ["DEFAULT_VOCABULARY", "AudioConfig"]
