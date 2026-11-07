"""Text-to-speech port: text out of the speaker, locally (R7, D7)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TextToSpeech(Protocol):
    """Adapter over a local voice."""

    async def speak(self, text: str) -> None:
        """Say ``text``; return when playback ends."""
        ...
