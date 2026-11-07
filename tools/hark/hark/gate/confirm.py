"""The spoken yes, with the F6 checks (D6, H3, F8).

A yes counts only if all of these hold: there was an answer; its audio energy
is a number at or above the floor; the words, stripped of case and
punctuation, exactly match one of a short yes list (no near-matches: "yes"
sounds like other words); and they are not a known hallucination phrase. A
spoken no denies at once. Anything else is asked once more, then denied.
Silence denies at once.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from enum import StrEnum

from hark.gate.config import GateConfig
from hark.ports import SpeechToText, TextToSpeech, Transcript

RETRY_PROMPT = "I didn't catch that. Say yes or no."


class Answer(StrEnum):
    YES = "yes"
    NO = "no"
    UNCLEAR = "unclear"  # failed a check: ask again


@dataclass(frozen=True)
class Confirmation:
    confirmed: bool
    heard: str | None  # last thing heard; None means silence
    outcome: str  # "yes" | "no" | "silence" | "unclear"


def normalise(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", "", text.lower().replace("'", "")).split())


def judge(heard: Transcript, config: GateConfig) -> Answer:
    """The F6 checks on one transcript. Pure."""
    words = normalise(heard.text)
    if words in config.hallucinations:
        return Answer.UNCLEAR
    if words in config.no_phrases:
        return Answer.NO  # a no needs no energy check: denying is always safe
    if heard.energy is None or heard.energy < config.min_energy:
        return Answer.UNCLEAR
    if words in config.yes_phrases:
        return Answer.YES
    return Answer.UNCLEAR


class Confirmer:
    """Listens for the answer to a question already spoken; one retry."""

    def __init__(self, tts: TextToSpeech, stt: SpeechToText, config: GateConfig | None = None) -> None:
        self._tts = tts
        self._stt = stt
        self._config = config or GateConfig()

    async def confirm(self) -> Confirmation:
        deadline = time.monotonic() + self._config.window_s
        heard: str | None = None
        for attempt in range(2):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                transcript = await asyncio.wait_for(self._stt.listen(timeout=remaining), remaining + 1.0)
            except TimeoutError:
                transcript = None
            if transcript is None:
                return Confirmation(False, None, "silence")
            heard = transcript.text
            answer = judge(transcript, self._config)
            if answer is Answer.YES:
                return Confirmation(True, heard, "yes")
            if answer is Answer.NO:
                return Confirmation(False, heard, "no")
            if attempt == 0:
                await self._tts.speak(RETRY_PROMPT)
        return Confirmation(False, heard, "unclear")
