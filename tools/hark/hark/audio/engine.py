"""The Pipecat boundary (D1): mic → VAD → tap → speaker, in a background task.

Pipecat pushes frames; Hark's ports pull (``wait()``, ``listen()``). The tap
bridges the two: it turns frames into a mic fan-out, one utterance at a time
(handed over through a future), and a "playback ended" signal. This is the
only module in Hark that imports Pipecat.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import AsyncIterable, AsyncIterator
from contextlib import asynccontextmanager, suppress

from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    BotStoppedSpeakingFrame,
    Frame,
    InputAudioRawFrame,
    TTSAudioRawFrame,
    TTSStoppedFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.audio.vad_processor import VADProcessor
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams
from pipecat.workers.runner import WorkerRunner

from hark.audio.config import AudioConfig
from hark.audio.io import Utterance
from hark.events import now

_SAMPLE_BYTES = 2  # 16-bit mono


class _Tap(FrameProcessor):
    """Hands the frames Hark cares about to the engine; drops mic audio after VAD."""

    def __init__(self, engine: PipecatAudioEngine) -> None:
        super().__init__(name="hark-tap")
        self._engine = engine

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)
        downstream = direction == FrameDirection.DOWNSTREAM
        if isinstance(frame, InputAudioRawFrame):
            self._engine._on_audio(frame.audio)
            return  # nothing past here needs mic audio
        if downstream and isinstance(frame, VADUserStartedSpeakingFrame):
            self._engine._on_speech_started()
        elif downstream and isinstance(frame, VADUserStoppedSpeakingFrame):
            self._engine._on_speech_stopped()
        elif not downstream and isinstance(frame, BotStoppedSpeakingFrame):
            self._engine._playback_ended.set()
        await self.push_frame(frame, direction)


class PipecatAudioEngine:
    """Owns the mic and speaker; shared by the three audio adapters."""

    def __init__(self, config: AudioConfig) -> None:
        self.config = config
        self.input_sample_rate = config.input_sample_rate
        self.output_sample_rate = config.output_sample_rate

        self._subscribers: set[asyncio.Queue[bytes]] = set()
        self._pre_roll: deque[bytes] = deque()
        self._pre_roll_bytes = 0
        self._pre_roll_limit = int(config.pre_roll_secs * self.input_sample_rate) * _SAMPLE_BYTES

        self._armed = False
        self._buffer: bytearray | None = None
        self._lead_bytes = 0
        self._speech_started = asyncio.Event()
        self._utterance: asyncio.Future[Utterance] | None = None
        self._listen_lock = asyncio.Lock()

        self._playback_ended = asyncio.Event()
        self._play_lock = asyncio.Lock()

        self._worker: PipelineWorker | None = None
        self._runner: WorkerRunner | None = None
        self._run_task: asyncio.Task[None] | None = None

    # -- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        if self._run_task:
            return
        cfg = self.config
        transport = LocalAudioTransport(
            LocalAudioTransportParams(
                audio_in_enabled=True,
                audio_in_sample_rate=cfg.input_sample_rate,
                audio_out_enabled=True,
                audio_out_sample_rate=cfg.output_sample_rate,
            )
        )
        vad = VADProcessor(
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(start_secs=cfg.vad_start_secs, stop_secs=cfg.vad_stop_secs)
            )
        )
        pipeline = Pipeline([transport.input(), vad, _Tap(self), transport.output()])
        self._worker = PipelineWorker(
            pipeline,
            params=PipelineParams(
                audio_in_sample_rate=cfg.input_sample_rate,
                audio_out_sample_rate=cfg.output_sample_rate,
            ),
            enable_rtvi=False,
            enable_turn_tracking=False,
            idle_timeout_secs=None,  # always on: never stop for lack of speech
        )
        started = asyncio.Event()

        @self._worker.event_handler("on_pipeline_started")
        async def _on_started(_worker, _frame):
            started.set()

        self._runner = WorkerRunner(handle_sigint=False)
        await self._runner.add_workers(self._worker)
        self._run_task = asyncio.create_task(self._runner.run())
        await asyncio.wait_for(started.wait(), timeout=15)
        logger.info("hark audio engine started")

    async def stop(self) -> None:
        if not self._run_task:
            return
        assert self._runner
        await self._runner.cancel()
        with suppress(asyncio.CancelledError):
            await self._run_task
        self._run_task = None

    # -- AudioIO ------------------------------------------------------------

    @asynccontextmanager
    async def frames(self) -> AsyncIterator[asyncio.Queue[bytes]]:
        queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=200)  # ~4 s at 20 ms frames
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)

    async def next_utterance(
        self, start_timeout: float | None, max_secs: float
    ) -> Utterance | None:
        async with self._listen_lock:
            loop = asyncio.get_running_loop()
            self._utterance = loop.create_future()
            self._speech_started.clear()
            self._armed = True
            try:
                try:
                    await asyncio.wait_for(self._speech_started.wait(), start_timeout)
                except TimeoutError:
                    return None
                try:
                    return await asyncio.wait_for(asyncio.shield(self._utterance), max_secs)
                except TimeoutError:
                    self._finish(ended_at=now(), vad_ended=False)  # hit the ceiling: cut
                    return self._utterance.result()
            finally:
                self._armed = False
                self._buffer = None

    async def play(self, audio: bytes | AsyncIterable[bytes], sample_rate: int) -> None:
        async with self._play_lock:
            worker = self._require_worker()
            self._playback_ended.clear()
            seconds = 0.0
            async for chunk in _chunks(audio):
                await worker.queue_frame(
                    TTSAudioRawFrame(audio=chunk, sample_rate=sample_rate, num_channels=1)
                )
                seconds += len(chunk) / _SAMPLE_BYTES / sample_rate
            if not seconds:
                return
            # The output transport handles frames in order, so this "stopped" frame is
            # reached only after the last chunk has been written to the speaker.
            await worker.queue_frame(TTSStoppedFrame())
            await asyncio.wait_for(self._playback_ended.wait(), timeout=seconds + 5)

    # -- called by the tap --------------------------------------------------

    def _on_audio(self, pcm: bytes) -> None:
        for queue in self._subscribers:
            if queue.full():
                queue.get_nowait()  # a slow reader loses the oldest audio, not the newest
            queue.put_nowait(pcm)
        if self._buffer is not None:
            self._buffer.extend(pcm)
            return
        self._pre_roll.append(pcm)
        self._pre_roll_bytes += len(pcm)
        while self._pre_roll_bytes > self._pre_roll_limit and len(self._pre_roll) > 1:
            self._pre_roll_bytes -= len(self._pre_roll.popleft())

    def _on_speech_started(self) -> None:
        if not self._armed or self._buffer is not None:
            return
        self._buffer = bytearray(b"".join(self._pre_roll))
        self._lead_bytes = len(self._buffer)
        self._speech_started.set()

    def _on_speech_stopped(self) -> None:
        if self._armed and self._buffer is not None:
            self._finish(ended_at=now(), vad_ended=True)

    def _finish(self, ended_at: float, vad_ended: bool) -> None:
        if self._buffer is None or self._utterance is None or self._utterance.done():
            return
        pcm = bytes(self._buffer)
        rate = self.input_sample_rate
        # VAD fires start_secs into speech and stop_secs after it; trim both edges.
        start = max(0, self._lead_bytes - int(self.config.vad_start_secs * rate) * _SAMPLE_BYTES)
        tail = int(self.config.vad_stop_secs * rate) * _SAMPLE_BYTES if vad_ended else 0
        voiced = pcm[start : max(start, len(pcm) - tail)]
        self._utterance.set_result(
            Utterance(pcm=pcm, voiced=voiced, sample_rate=rate, ended_at=ended_at)
        )
        self._buffer = None

    def _require_worker(self) -> PipelineWorker:
        if self._worker is None:
            raise RuntimeError("audio engine not started")
        return self._worker


async def _chunks(audio: bytes | AsyncIterable[bytes]) -> AsyncIterator[bytes]:
    if isinstance(audio, bytes):
        yield audio
        return
    async for chunk in audio:
        if chunk:
            yield chunk
