"""Lane A adapters against a fake engine: no Pipecat, no sound card, no servers."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterable
from contextlib import asynccontextmanager

import httpx
import numpy as np
import pytest

from hark.audio.config import AudioConfig
from hark.audio.io import Utterance
from hark.audio.kokoro import KokoroClient
from hark.audio.levels import is_non_speech, is_silence_hallucination, normalise, rms
from hark.audio.speech_to_text import WhisperSpeechToText
from hark.audio.text_to_speech import KokoroTextToSpeech
from hark.audio.wake_word import CHUNK_SAMPLES, OpenWakeWord
from hark.audio.whisper import WhisperClient
from hark.ports import SpeechToText, TextToSpeech, WakeWord

RATE = 16000


def tone(level: float, secs: float = 0.5) -> bytes:
    """A sine wave whose RMS is ``level`` (of int16 full scale)."""
    t = np.arange(int(secs * RATE)) / RATE
    return (np.sin(2 * np.pi * 220 * t) * level * np.sqrt(2) * 32767).astype(np.int16).tobytes()


class FakeIO:
    """Stands in for PipecatAudioEngine."""

    input_sample_rate = RATE
    output_sample_rate = 24000

    def __init__(self, utterances=(), frames=()) -> None:
        self._utterances = list(utterances)
        self._frames = list(frames)
        self.played: list[bytes] = []
        self.listen_calls: list[tuple[float | None, float]] = []

    @asynccontextmanager
    async def frames(self):
        queue: asyncio.Queue[bytes] = asyncio.Queue()
        for frame in self._frames:
            queue.put_nowait(frame)
        yield queue

    async def next_utterance(self, start_timeout, max_secs):
        self.listen_calls.append((start_timeout, max_secs))
        return self._utterances.pop(0) if self._utterances else None

    async def play(self, audio: bytes | AsyncIterable[bytes], sample_rate: int) -> None:
        if isinstance(audio, bytes):
            self.played.append(audio)
        else:
            self.played.append(b"".join([chunk async for chunk in audio]))


def whisper_returning(text: str, seen: list[dict] | None = None) -> WhisperClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append({"body": request.content, "url": str(request.url)})
        return httpx.Response(200, json={"text": text})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return WhisperClient("http://whisper/v1/audio/transcriptions", client=client)


def utterance(pcm: bytes, ended_at: float = 123.0) -> Utterance:
    return Utterance(pcm=pcm, voiced=pcm, sample_rate=RATE, ended_at=ended_at)


# -- ports -------------------------------------------------------------------


class FakeScorer:
    def __init__(self, scores: list[float], key: str = "hey_jarvis") -> None:
        self.scores = list(scores)
        self.key = key
        self.resets = 0

    def predict(self, x):
        assert x.dtype == np.int16 and x.size == CHUNK_SAMPLES
        return {self.key: self.scores.pop(0) if self.scores else 0.0}

    def reset(self) -> None:
        self.resets += 1


def test_adapters_satisfy_ports():
    io = FakeIO()
    assert isinstance(OpenWakeWord(io, FakeScorer([]), "hey_jarvis"), WakeWord)
    assert isinstance(WhisperSpeechToText(io, whisper_returning("")), SpeechToText)
    assert isinstance(KokoroTextToSpeech(io, KokoroClient("http://kokoro")), TextToSpeech)


# -- wake word ---------------------------------------------------------------


def test_wake_returns_on_first_score_over_threshold_and_chimes():
    # 20 ms frames, as the mic delivers them; 4 chunks' worth.
    frames = [b"\x00\x00" * 320] * (4 * CHUNK_SAMPLES // 320)
    scorer = FakeScorer([0.1, 0.3, 0.9, 0.95], key="hey_jarvis_v0.1")
    io = FakeIO(frames=frames)
    wake = asyncio.run(OpenWakeWord(io, scorer, "hey_jarvis_v0.1", threshold=0.5).wait())
    assert wake.phrase == "hey jarvis"
    assert wake.score == pytest.approx(0.9)
    assert scorer.scores == [0.95]  # stopped at the first hit
    assert scorer.resets == 2  # before listening and after the hit
    assert len(io.played) == 1  # the "listening" chime


# -- speech to text ----------------------------------------------------------


def listen(stt: WhisperSpeechToText, timeout: float | None = 5.0):
    async def run():
        result = await stt.listen(timeout)
        await asyncio.sleep(0)  # let the cue task finish
        return result

    return asyncio.run(run())


def test_listen_returns_text_end_of_speech_time_and_energy():
    io = FakeIO(utterances=[utterance(tone(0.1), ended_at=42.5)])
    t = listen(WhisperSpeechToText(io, whisper_returning(" Open labs. ")))
    assert t is not None
    assert t.text == "Open labs."
    assert t.speech_ended_at == 42.5  # VAD's moment, not when Whisper finished (R6)
    assert t.energy == pytest.approx(0.1, rel=0.02)
    assert len(io.played) == 1  # the "got it" chime


def test_listen_passes_timeout_and_returns_none_on_silence():
    io = FakeIO(utterances=[])
    stt = WhisperSpeechToText(io, whisper_returning("never asked"), max_utterance_secs=12)
    assert listen(stt, timeout=3.0) is None
    assert io.listen_calls == [(3.0, 12)]
    assert io.played == []


@pytest.mark.parametrize("text", ["", "  ", "[BLANK_AUDIO]", "(silence)", "...", "[Music] [Music]"])
def test_listen_never_returns_empty_or_non_speech(text):
    io = FakeIO(utterances=[utterance(tone(0.2))])
    assert listen(WhisperSpeechToText(io, whisper_returning(text))) is None


@pytest.mark.parametrize("text", ["Thank you.", "Thank you. Thank you.", "Thanks for watching!", "you"])
def test_quiet_hallucination_rejected_loud_kept(text):
    quiet = FakeIO(utterances=[utterance(tone(0.002))])
    assert listen(WhisperSpeechToText(quiet, whisper_returning(text), min_energy=0.01)) is None

    loud = FakeIO(utterances=[utterance(tone(0.1))])
    t = listen(WhisperSpeechToText(loud, whisper_returning(text), min_energy=0.01))
    assert t is not None and t.text == text


def test_quiet_yes_is_returned_with_its_energy_for_the_gate():
    # Not a known hallucination, so it is returned; the gate judges it by energy (H3).
    io = FakeIO(utterances=[utterance(tone(0.003))])
    t = listen(WhisperSpeechToText(io, whisper_returning("Yes."), min_energy=0.01))
    assert t is not None and t.energy is not None and t.energy < 0.01


def test_vocabulary_prompt_is_sent_to_whisper():
    seen: list[dict] = []
    prompt = AudioConfig().vocabulary_prompt
    io = FakeIO(utterances=[utterance(tone(0.1))])
    listen(WhisperSpeechToText(io, whisper_returning("Ask Claude", seen), prompt=prompt))
    body = seen[0]["body"].decode("latin-1")
    assert 'name="prompt"' in body and "Claude, Claude Code, Hark" in body
    assert 'name="language"' in body and "RIFF" in body  # a WAV file went up


# -- text to speech ----------------------------------------------------------


def test_speak_streams_kokoro_pcm_to_the_speaker():
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, content=b"\x01\x02" * 1000)

    kokoro = KokoroClient(
        "http://kokoro/v1/audio/speech",
        voice="af_sky",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    io = FakeIO()
    asyncio.run(KokoroTextToSpeech(io, kokoro).speak("on it"))
    assert seen == [{"model": "kokoro", "input": "on it", "voice": "af_sky", "response_format": "pcm"}]
    assert io.played == [b"\x01\x02" * 1000]


def test_speak_waits_out_a_kokoro_restart():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(200, content=b"\x00\x01" * 10)

    kokoro = KokoroClient(
        "http://kokoro/v1/audio/speech",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    io = FakeIO()
    asyncio.run(KokoroTextToSpeech(io, kokoro).speak("on it"))
    assert calls == 2 and io.played == [b"\x00\x01" * 10]


def test_speak_nothing_plays_nothing():
    io = FakeIO()
    asyncio.run(KokoroTextToSpeech(io, KokoroClient("http://unused")).speak("  "))
    assert io.played == []


# -- levels and config -------------------------------------------------------


def test_rms_scale():
    assert rms(b"") == 0.0
    assert rms(b"\x00\x00" * 100) == 0.0
    assert rms(tone(0.25)) == pytest.approx(0.25, rel=0.02)


def test_normalise_collapses_repeats_and_punctuation():
    assert normalise("Thank you. Thank you. Thank you.") == "thank you"
    assert normalise("Open labs!") == "open labs"
    assert is_non_speech("[BLANK_AUDIO]") and is_non_speech("…") and not is_non_speech("no")
    assert not is_silence_hallucination("open labs", 0.0, 0.01)


def test_config_from_toml(tmp_path):
    path = tmp_path / "hark.toml"
    path.write_text('[audio]\nwake_model = "/models/hey_hark.onnx"\nvocabulary = ["Claude", "Hark"]\n')
    config = AudioConfig.from_toml(path)
    assert config.wake_model == "/models/hey_hark.onnx"
    assert config.vocabulary_prompt == "Claude, Hark."

    path.write_text('[audio]\nwake_modle = "typo"\n')
    with pytest.raises(ValueError, match="wake_modle"):
        AudioConfig.from_toml(path)
