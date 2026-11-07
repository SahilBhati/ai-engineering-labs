from __future__ import annotations

from hark.ports import Wake


class StubWakeWord:
    """Wakes immediately, as if the phrase was just heard."""

    def __init__(self, phrase: str = "hey hark") -> None:
        self.phrase = phrase

    async def wait(self) -> Wake:
        return Wake(phrase=self.phrase, score=1.0)
