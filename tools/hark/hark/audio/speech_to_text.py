"""SpeechToText adapter: VAD-bounded capture, then the whisper.cpp server (D3)."""

from __future__ import annotations

import asyncio

from loguru import logger

from hark.audio import cues
from hark.audio.io import AudioIO
from hark.audio.levels import is_non_speech, is_silence_hallucination, rms
from hark.audio.whisper import WhisperClient
from hark.ports import Transcript


class WhisperSpeechToText:
    """``listen()`` owns capture, VAD and transcription; core never sees audio (D1)."""

    def __init__(
        self,
        io: AudioIO,
        whisper: WhisperClient,
        *,
        prompt: str = "",
        min_energy: float = 0.02,
        max_utterance_secs: float = 30.0,
        cue: bool = True,
    ) -> None:
        self._io = io
        self._whisper = whisper
        self.prompt = prompt
        self.min_energy = min_energy
        self.max_utterance_secs = max_utterance_secs
        self._cue = cue
        self._cue_tasks: set[asyncio.Task[None]] = set()

    async def listen(self, timeout: float | None = None) -> Transcript | None:
        """``timeout`` bounds the wait for speech to start; a started utterance runs to its end."""
        utterance = await self._io.next_utterance(timeout, self.max_utterance_secs)
        if utterance is None:
            return None
        if self._cue:  # D8: short chime = "got it"; plays while we transcribe
            self._play_cue()
        energy = rms(utterance.voiced)
        text = await self._whisper.transcribe(utterance.pcm, utterance.sample_rate, self.prompt)
        if is_non_speech(text) or is_silence_hallucination(text, energy, self.min_energy):
            logger.info(f"dropped utterance {text!r} (energy {energy:.4f})")
            return None
        return Transcript(text=text, speech_ended_at=utterance.ended_at, energy=energy)

    def _play_cue(self) -> None:
        rate = self._io.output_sample_rate
        task = asyncio.create_task(self._io.play(cues.got_it(rate), rate))
        self._cue_tasks.add(task)
        task.add_done_callback(self._cue_tasks.discard)
