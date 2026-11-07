"""TextToSpeech adapter: the Kokoro server, streamed to the speaker (D7)."""

from __future__ import annotations

from hark.audio.io import AudioIO
from hark.audio.kokoro import KokoroClient

KOKORO_SAMPLE_RATE = 24000


class KokoroTextToSpeech:
    def __init__(self, io: AudioIO, kokoro: KokoroClient) -> None:
        self._io = io
        self._kokoro = kokoro

    async def speak(self, text: str) -> None:
        if text.strip():
            # Playback starts on the first chunk, not after the whole reply is synthesised.
            await self._io.play(self._kokoro.stream(text), KOKORO_SAMPLE_RATE)
