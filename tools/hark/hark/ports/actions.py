"""Action registry port: named, fast, local actions (R4).

Pattern: Command (each action is an object you run) + Registry (looked up
by name).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class Action(Protocol):
    name: str
    phrases: Sequence[str]  # example phrases the router matches against (D4)

    async def run(self, args: Mapping[str, str]) -> str:
        """Do the action; return a short spoken confirmation."""
        ...


@runtime_checkable
class ActionRegistry(Protocol):
    def get(self, name: str) -> Action:
        """Raise KeyError for an unknown name."""
        ...

    def all(self) -> Sequence[Action]: ...
