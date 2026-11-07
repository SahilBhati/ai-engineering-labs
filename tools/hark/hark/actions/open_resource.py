"""OpenResource: open a known URL, app or path by name with macOS ``open`` (R4).

Pattern: Command. One instance per configured resource, so the action name
is the resource and the router needs no argument extraction.

Resources live outside the repo (they hold personal URLs), in TOML:

```toml
[[resource]]
name = "labs_github"                 # unique action name
spoken = "the labs GitHub page"      # optional; used in the reply
url = "https://github.com/you/repo"  # exactly one of url, app, path
phrases = ["open my labs GitHub page", "open labs github"]
```
"""

from __future__ import annotations

import asyncio
import os
import tomllib
from collections.abc import Awaitable, Callable, Mapping, Sequence
from pathlib import Path

from hark.actions.registry import Registry

DEFAULT_CONFIG = Path("~/.config/hark/actions.toml")

type Opener = Callable[[Sequence[str]], Awaitable[int]]


async def run_open(argv: Sequence[str]) -> int:
    """Run ``open`` without a shell; return its exit code."""
    proc = await asyncio.create_subprocess_exec(
        *argv, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    return await proc.wait()


class OpenResource:
    def __init__(
        self,
        name: str,
        phrases: Sequence[str],
        argv: Sequence[str],
        spoken: str | None = None,
        opener: Opener = run_open,
    ) -> None:
        self.name = name
        self.phrases = list(phrases)
        self.argv = list(argv)
        self.spoken = spoken or name.replace("_", " ")
        self._opener = opener

    async def run(self, args: Mapping[str, str]) -> str:
        code = await self._opener(self.argv)
        return f"Opening {self.spoken}." if code == 0 else f"Couldn't open {self.spoken}."


def _argv(entry: Mapping[str, object]) -> list[str]:
    targets = {k: entry[k] for k in ("url", "app", "path") if k in entry}
    if len(targets) != 1:
        raise ValueError(f"resource {entry.get('name')!r}: give exactly one of url, app, path")
    kind, target = targets.popitem()
    if not isinstance(target, str) or not target:
        raise ValueError(f"resource {entry.get('name')!r}: {kind} must be a non-empty string")
    if kind == "url" and not target.startswith(("https://", "http://")):
        raise ValueError(f"resource {entry.get('name')!r}: url must start with http(s)://")
    if kind == "app":
        return ["open", "-a", target]
    if kind == "path":
        return ["open", os.path.expanduser(target)]
    return ["open", target]


def load_resources(path: Path = DEFAULT_CONFIG, opener: Opener = run_open) -> Registry:
    """Build a registry of ``OpenResource`` actions from a TOML config."""
    with open(path.expanduser(), "rb") as f:
        config = tomllib.load(f)
    registry = Registry()
    for entry in config.get("resource", []):
        phrases = entry.get("phrases")
        if not isinstance(phrases, list) or not all(isinstance(p, str) for p in phrases):
            raise ValueError(f"resource {entry.get('name')!r}: phrases must be a list of strings")
        registry.register(
            OpenResource(
                name=entry["name"],
                phrases=phrases,
                argv=_argv(entry),
                spoken=entry.get("spoken"),
                opener=opener,
            )
        )
    return registry
