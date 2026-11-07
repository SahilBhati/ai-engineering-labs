"""Client for an OpenAI-compatible transcription endpoint (the whisper.cpp server, D3)."""

from __future__ import annotations

import io
import wave

import httpx


def wav_bytes(pcm: bytes, sample_rate: int) -> bytes:
    """Wrap 16-bit mono PCM in a WAV header."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


class WhisperClient:
    """Adapter over ``POST /v1/audio/transcriptions``; swapping servers is a URL change."""

    def __init__(
        self,
        url: str,
        *,
        language: str = "en",
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.url = url
        self.language = language
        self._client = client or httpx.AsyncClient(timeout=timeout)

    async def transcribe(self, pcm: bytes, sample_rate: int, prompt: str = "") -> str:
        data = {"response_format": "json", "temperature": "0", "language": self.language}
        if prompt:
            data["prompt"] = prompt  # biases decoding toward these words (F1)
        files = {"file": ("utterance.wav", wav_bytes(pcm, sample_rate), "audio/wav")}
        response = await self._client.post(self.url, data=data, files=files)
        response.raise_for_status()
        return str(response.json().get("text", "")).strip()

    async def aclose(self) -> None:
        await self._client.aclose()
