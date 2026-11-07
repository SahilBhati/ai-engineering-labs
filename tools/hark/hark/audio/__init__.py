"""Audio adapters: wake word, speech-to-text, text-to-speech (lane A).

The only package in Hark allowed to import Pipecat (D1), and only in
``engine.py``. ``build_audio`` wires the three adapters to one shared mic and
speaker (pattern: Factory).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from hark.audio.config import AudioConfig
from hark.audio.kokoro import KokoroClient
from hark.audio.speech_to_text import WhisperSpeechToText
from hark.audio.text_to_speech import KokoroTextToSpeech
from hark.audio.wake_word import OpenWakeWord, load_openwakeword
from hark.audio.whisper import WhisperClient

if TYPE_CHECKING:
    from hark.audio.engine import PipecatAudioEngine


@dataclass
class Audio:
    engine: PipecatAudioEngine
    wake_word: OpenWakeWord
    speech_to_text: WhisperSpeechToText
    text_to_speech: KokoroTextToSpeech

    async def start(self) -> None:
        await self.engine.start()

    async def stop(self) -> None:
        await self.engine.stop()


def build_audio(config: AudioConfig | None = None) -> Audio:
    """Build the adapters on one engine. Call ``start()`` before using them."""
    from hark.audio.engine import PipecatAudioEngine  # Pipecat loads only when audio is wanted

    config = config or AudioConfig()
    engine = PipecatAudioEngine(config)
    scorer, key = load_openwakeword(config.wake_model)
    return Audio(
        engine=engine,
        wake_word=OpenWakeWord(
            engine, scorer, key, threshold=config.wake_threshold, cue=config.cues
        ),
        speech_to_text=WhisperSpeechToText(
            engine,
            WhisperClient(config.whisper_url, language=config.language),
            prompt=config.vocabulary_prompt,
            min_energy=config.min_energy,
            max_utterance_secs=config.max_utterance_secs,
            cue=config.cues,
        ),
        text_to_speech=KokoroTextToSpeech(
            engine, KokoroClient(config.kokoro_url, voice=config.voice)
        ),
    )


__all__ = [
    "Audio",
    "AudioConfig",
    "KokoroTextToSpeech",
    "OpenWakeWord",
    "WhisperSpeechToText",
    "build_audio",
]
