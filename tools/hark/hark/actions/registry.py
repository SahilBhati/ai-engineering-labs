"""Action registry: named actions, looked up by name (pattern: Registry)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from hark.ports import Action


class Registry:
    def __init__(self, actions: Iterable[Action] = ()) -> None:
        self._by_name: dict[str, Action] = {}
        for action in actions:
            self.register(action)

    def register(self, action: Action) -> None:
        if action.name in self._by_name:
            raise ValueError(f"duplicate action name: {action.name!r}")
        if not action.phrases:
            raise ValueError(f"action {action.name!r} has no phrases")
        self._by_name[action.name] = action

    def get(self, name: str) -> Action:
        return self._by_name[name]

    def all(self) -> Sequence[Action]:
        return list(self._by_name.values())
