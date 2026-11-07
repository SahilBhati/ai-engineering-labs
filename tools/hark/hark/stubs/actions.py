from __future__ import annotations

from collections.abc import Mapping, Sequence

from hark.ports import Action


class StubAction:
    """Records each run and replies with a fixed confirmation."""

    def __init__(self, name: str, phrases: Sequence[str], reply: str = "Done.") -> None:
        self.name = name
        self.phrases = phrases
        self.reply = reply
        self.runs: list[Mapping[str, str]] = []

    async def run(self, args: Mapping[str, str]) -> str:
        self.runs.append(args)
        return self.reply


class StubActionRegistry:
    def __init__(self, actions: Sequence[Action]) -> None:
        self._by_name = {a.name: a for a in actions}

    def get(self, name: str) -> Action:
        return self._by_name[name]

    def all(self) -> Sequence[Action]:
        return list(self._by_name.values())
