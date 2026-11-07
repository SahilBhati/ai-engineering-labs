"""Lane A against the real servers, mic and speaker. Skipped unless --hardware.

Needs the whisper.cpp server (:2022) and Kokoro (:8880) running. The speaker
test makes a sound; the mic is opened but nobody needs to talk.
"""

from __future__ import annotations

import asyncio

import numpy as np
import pytest

from hark.audio import AudioConfig, build_audio
from hark.audio.kokoro import KokoroClient
from hark.audio.wake_word import CHUNK_SAMPLES, load_openwakeword
from hark.audio.whisper import WhisperClient

pytestmark = pytest.mark.hardware


async def kokoro_16k(text: str) -> bytes:
    from scipy.signal import resample_poly

    config = AudioConfig()
    kokoro = KokoroClient(config.kokoro_url, voice=config.voice)
    pcm24 = b"".join([chunk async for chunk in kokoro.stream(text)])
    await kokoro.aclose()
    x = resample_poly(np.frombuffer(pcm24, np.int16).astype(np.float32), 2, 3)
    return np.clip(x, -32768, 32767).astype(np.int16).tobytes()


def test_whisper_server_hears_claude_with_the_vocabulary_prompt():
    async def run():
        pcm = await kokoro_16k("Ask Claude to open the Hark backlog.")
        whisper = WhisperClient(AudioConfig().whisper_url)
        text = await whisper.transcribe(pcm, 16000, AudioConfig().vocabulary_prompt)
        await whisper.aclose()
        return text

    text = asyncio.run(run())
    assert "claude" in text.lower() and "hark" in text.lower()


def test_wake_model_fires_on_the_phrase_and_not_on_a_command():
    scorer, key = load_openwakeword(AudioConfig().wake_model)

    def peak(pcm: bytes) -> float:
        scorer.reset()
        x = np.concatenate([np.frombuffer(pcm, np.int16), np.zeros(CHUNK_SAMPLES * 10, np.int16)])
        return max(scorer.predict(x[i : i + CHUNK_SAMPLES])[key] for i in range(0, x.size - CHUNK_SAMPLES, CHUNK_SAMPLES))

    assert peak(asyncio.run(kokoro_16k("Hey Jarvis."))) >= 0.5
    assert peak(asyncio.run(kokoro_16k("Open the labs repo."))) < 0.5


def test_engine_starts_listens_and_speaks():
    async def run():
        audio = build_audio()
        await audio.start()
        try:
            await audio.text_to_speech.speak("On it.")
            # A short wait on a quiet room: None, never "" or "Thank you."
            return await audio.speech_to_text.listen(timeout=1.0)
        finally:
            await audio.stop()

    transcript = asyncio.run(run())
    assert transcript is None or transcript.text.strip()
