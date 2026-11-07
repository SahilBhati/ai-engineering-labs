from __future__ import annotations


class StubTextToSpeech:
    """Records what would have been said."""

    def __init__(self) -> None:
        self.spoken: list[str] = []

    async def speak(self, text: str) -> None:
        self.spoken.append(text)
