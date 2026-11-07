from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from hark.events import now
from hark.ports import Transcript


class StubSpeechToText:
    """Plays back scripted utterances in order; None stands for silence."""

    def __init__(self, utterances: Iterable[str | None]) -> None:
        self._utterances = deque(utterances)

    async def listen(self, timeout: float | None = None) -> Transcript | None:
        text = self._utterances.popleft() if self._utterances else None
        if text is None:
            return None
        return Transcript(text=text, speech_ended_at=now(), energy=1.0)
