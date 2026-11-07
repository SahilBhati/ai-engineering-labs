"""Lane A lab numbers: openWakeWord on Apple Silicon, and STT with vs without a vocabulary prompt.

    uv run python bench/lane_a.py stt [--clips DIR]   # 30 utterances, p50/p95, term accuracy
    uv run python bench/lane_a.py wake                # detection on synthetic clips + per-chunk cost
    uv run python bench/lane_a.py idle [--secs 60]    # CPU of the live engine waiting for the wake word

With no --clips, the 30 utterances are synthesised by the Kokoro server
(two voices) and cached in bench/clips/. Point --clips at a folder of real
recordings named like the cache (00.wav … 29.wav) to measure real speech.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import resource
import statistics
import time
import wave
from pathlib import Path

import httpx
import numpy as np
from scipy.signal import resample_poly

from hark.audio import AudioConfig, build_audio
from hark.audio.wake_word import CHUNK_SAMPLES, load_openwakeword
from hark.audio.whisper import WhisperClient

HERE = Path(__file__).parent
CLIPS = HERE / "clips"
RESULTS = HERE / "results"

# (utterance, the project terms it must come back with)
UTTERANCES: list[tuple[str, list[str]]] = [
    ("Open labs.", ["labs"]),
    ("Ask Claude what's left in the build plan.", ["Claude"]),
    ("Hey Claude, summarise today's commits.", ["Claude"]),
    ("Start Claude Code in the labs repo.", ["Claude Code", "labs", "repo"]),
    ("Open the Hark backlog.", ["Hark"]),
    ("Run the Hark tests.", ["Hark"]),
    ("How does Pipecat handle barge-in?", ["Pipecat"]),
    ("Restart the Kokoro server.", ["Kokoro"]),
    ("Is the Whisper server bound to localhost?", ["Whisper"]),
    ("Retrain openWakeWord on a new phrase.", ["openWakeWord"]),
    ("Open ai-vault.", ["vault"]),
    ("Search the vault for the Pipecat decision.", ["vault", "Pipecat"]),
    ("Push the branch.", ["push"]),
    ("Git push to main.", ["push"]),
    ("Ask Claude to review the diff.", ["Claude"]),
    ("Tell Claude to stop.", ["Claude"]),
    ("What did Claude Code change in Hark?", ["Claude Code", "Hark"]),
    ("Open the labs site.", ["labs"]),
    ("Publish the next lesson to the labs site.", ["labs"]),
    ("Mute Hark for an hour.", ["Hark"]),
    ("Compare Kokoro voices.", ["Kokoro"]),
    ("Which Pipecat version are we on?", ["Pipecat"]),
    ("Open the repo in the editor.", ["repo"]),
    ("Claude, what's on my calendar?", ["Claude"]),
    ("Show the Hark event log.", ["Hark"]),
    ("Why is Whisper slow today?", ["Whisper"]),
    ("Ask Claude to draft the lab log.", ["Claude"]),
    ("Close labs.", ["labs"]),
    ("Yes.", ["yes"]),
    ("No.", ["no"]),
]
VOICES = ("af_sky", "am_michael")


def read_wav(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path)) as w:
        return w.readframes(w.getnframes()), w.getframerate()


def write_wav(path: Path, pcm: bytes, rate: int) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def to_16k(pcm24: bytes) -> bytes:
    x = np.frombuffer(pcm24, np.int16).astype(np.float32)
    return np.clip(resample_poly(x, 2, 3), -32768, 32767).astype(np.int16).tobytes()


def synthesise(text: str, voice: str, config: AudioConfig) -> bytes:
    body = {"model": "kokoro", "input": text, "voice": voice, "response_format": "pcm"}
    for _ in range(40):  # VoiceMode's Kokoro restarts every 25 requests
        try:
            r = httpx.post(config.kokoro_url, json=body, timeout=60)
            break
        except httpx.ConnectError:
            time.sleep(1)
    r.raise_for_status()
    return to_16k(r.content)


def ensure_clips(config: AudioConfig) -> Path:
    CLIPS.mkdir(exist_ok=True)
    for i, (text, _) in enumerate(UTTERANCES):
        path = CLIPS / f"{i:02d}.wav"
        if not path.exists():
            write_wav(path, synthesise(text, VOICES[i % 2], config), 16000)
    return CLIPS


def pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


async def bench_stt(clips: Path, config: AudioConfig) -> dict:
    whisper = WhisperClient(config.whisper_url, language=config.language)
    audio = [read_wav(clips / f"{i:02d}.wav") for i in range(len(UTTERANCES))]
    await whisper.transcribe(*audio[0])  # warm-up, not counted
    out: dict = {}
    for label, prompt in (("no_prompt", ""), ("prompt", config.vocabulary_prompt)):
        rows = []
        for (text, terms), (pcm, rate) in zip(UTTERANCES, audio, strict=True):
            t0 = time.perf_counter()
            heard = await whisper.transcribe(pcm, rate, prompt)
            secs = time.perf_counter() - t0
            hits = [term for term in terms if term.lower() in heard.lower()]
            rows.append({"said": text, "heard": heard, "secs": secs, "terms": terms, "hits": hits})
        latencies = [r["secs"] for r in rows]
        out[label] = {
            "p50": pct(latencies, 0.5),
            "p95": pct(latencies, 0.95),
            "term_hits": sum(len(r["hits"]) for r in rows),
            "terms": sum(len(r["terms"]) for r in rows),
            "rows": rows,
        }
    await whisper.aclose()
    return out


def bench_wake(config: AudioConfig) -> dict:
    scorer, key = load_openwakeword(config.wake_model)

    def peak(pcm: bytes) -> float:
        scorer.reset()
        x = np.frombuffer(pcm, np.int16)
        x = np.concatenate([np.zeros(CHUNK_SAMPLES * 10, np.int16), x, np.zeros(CHUNK_SAMPLES * 10, np.int16)])
        return max(scorer.predict(x[i : i + CHUNK_SAMPLES])[key] for i in range(0, x.size - CHUNK_SAMPLES, CHUNK_SAMPLES))

    positives = {f"{v}: {t}": synthesise(t, v, config) for v in ("af_sky", "am_michael", "bf_emma", "am_adam") for t in ("Hey Jarvis.", "Hey Jarvis, open labs.")}
    negatives = {f"af_sky: {t}": synthesise(t, "af_sky", config) for t, _ in UTTERANCES[:10]}
    pos = {k: float(peak(v)) for k, v in positives.items()}
    neg = {k: float(peak(v)) for k, v in negatives.items()}

    noise = (np.random.default_rng(0).normal(0, 300, CHUNK_SAMPLES * 500)).astype(np.int16)
    scorer.reset()
    t0, c0 = time.perf_counter(), time.process_time()
    for i in range(0, noise.size, CHUNK_SAMPLES):
        scorer.predict(noise[i : i + CHUNK_SAMPLES])
    wall, cpu = time.perf_counter() - t0, time.process_time() - c0
    return {
        "threshold": config.wake_threshold,
        "positives": pos,
        "negatives": neg,
        "detected": int(sum(s >= config.wake_threshold for s in pos.values())),
        "false_triggers": int(sum(s >= config.wake_threshold for s in neg.values())),
        "ms_per_80ms_chunk": wall / 500 * 1000,
        "cpu_share_of_one_core": cpu / (500 * 0.08),
    }


async def bench_idle(secs: float, config: AudioConfig) -> dict:
    audio = build_audio(config)
    await audio.start()
    waiter = asyncio.create_task(audio.wake_word.wait())
    await asyncio.sleep(3)  # settle
    r0, t0 = resource.getrusage(resource.RUSAGE_SELF), time.perf_counter()
    await asyncio.sleep(secs)
    r1, t1 = resource.getrusage(resource.RUSAGE_SELF), time.perf_counter()
    woke = waiter.done()
    waiter.cancel()
    await audio.stop()
    cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
    return {"secs": t1 - t0, "cpu_secs": cpu, "cpu_share_of_one_core": cpu / (t1 - t0), "woke_during_run": woke, "max_rss_mb": r1.ru_maxrss / 1e6}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", choices=["stt", "wake", "idle"])
    parser.add_argument("--clips", type=Path)
    parser.add_argument("--secs", type=float, default=60)
    args = parser.parse_args()
    config = AudioConfig()
    RESULTS.mkdir(exist_ok=True)
    if args.what == "stt":
        result = asyncio.run(bench_stt(args.clips or ensure_clips(config), config))
        for label, r in result.items():
            print(f"{label:10s} p50 {r['p50']:.3f}s  p95 {r['p95']:.3f}s  terms {r['term_hits']}/{r['terms']}")
            for row in r["rows"]:
                if len(row["hits"]) < len(row["terms"]):
                    print(f"    missed {row['said']!r} → {row['heard']!r}")
    elif args.what == "wake":
        result = bench_wake(config)
        print(json.dumps(result, indent=2))
    else:
        result = asyncio.run(bench_idle(args.secs, config))
        print(json.dumps(result, indent=2))
    (RESULTS / f"{args.what}.json").write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
