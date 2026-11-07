"""Gate settings: the yes list, the hallucination list, the energy floor (H3, F6).

Defaults live here; ``~/.config/hark/gate.toml`` (a ``[gate]`` table) overrides
any of them. See ``examples/gate.toml``.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

DEFAULT_PATH = Path.home() / ".config" / "hark" / "gate.toml"

# Whisper's output for silence or noise (F6). A hit is never a yes.
HALLUCINATIONS = (
    "thank you", "thanks", "thanks for watching", "thank you for watching",
    "thank you so much for watching", "please subscribe", "subscribe", "you",
    "bye", "bye bye", "okay", "oh", "so", "hmm",
)  # fmt: skip


@dataclass(frozen=True)
class GateConfig:
    yes_phrases: tuple[str, ...] = ("yes", "yeah", "yep", "do it", "go ahead", "confirm")
    no_phrases: tuple[str, ...] = ("no", "nope", "nah", "cancel", "stop", "dont", "deny")
    hallucinations: tuple[str, ...] = HALLUCINATIONS
    # Conservative start (rejects when unsure): above the adapter's own 0.02
    # floor and ~3x the measured room noise of 0.0096. Calibrate on real
    # speech (H8).
    min_energy: float = 0.03
    window_s: float = 10.0  # total time to answer, covering the one retry

    @classmethod
    def load(cls, path: Path | None = None) -> GateConfig:
        path = path or DEFAULT_PATH
        if not path.exists():
            return cls()
        table = tomllib.loads(path.read_text()).get("gate", {})
        known = {f.name for f in fields(cls)}
        unknown = set(table) - known
        if unknown:
            raise ValueError(f"unknown gate setting(s) in {path}: {sorted(unknown)}")
        values = {k: tuple(v) if isinstance(v, list) else v for k, v in table.items()}
        return cls(**values)
