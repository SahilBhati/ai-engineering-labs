"""Hand check for lane A: say the wake phrase, say a sentence, hear it back.

    uv run python -m hark.audio            # loops until Ctrl-C
    uv run python -m hark.audio --once
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from loguru import logger

from hark.audio import AudioConfig, build_audio
from hark.events import now


async def main(once: bool, config_path: str | None) -> None:
    config = AudioConfig.from_toml(config_path) if config_path else AudioConfig()
    audio = build_audio(config)
    await audio.start()
    try:
        await audio.text_to_speech.speak("Hark is ready.")
        while True:
            print(f"say '{audio.wake_word.phrase}'…", flush=True)
            wake = await audio.wake_word.wait()
            print(f"  woke (score {wake.score:.2f}); say a sentence", flush=True)
            transcript = await audio.speech_to_text.listen(timeout=8)
            if transcript is None:
                print("  heard nothing", flush=True)
                await audio.text_to_speech.speak("I didn't catch that.")
            else:
                stt_secs = now() - transcript.speech_ended_at
                print(
                    f"  heard {transcript.text!r}  energy {transcript.energy:.4f}  "
                    f"end-of-speech → text {stt_secs:.2f}s",
                    flush=True,
                )
                await audio.text_to_speech.speak(transcript.text)
            if once:
                return
    finally:
        await audio.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--config", help="TOML file with an [audio] table")
    parser.add_argument("--debug", action="store_true", help="show Pipecat's debug log")
    args = parser.parse_args()
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if args.debug else "WARNING")
    try:
        asyncio.run(main(args.once, args.config))
    except KeyboardInterrupt:
        pass
