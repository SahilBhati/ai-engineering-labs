from __future__ import annotations

from hark.ports import ActionRegistry, FastAction, Route, ToBrain


class StubRouter:
    """Exact phrase match against the registry; anything else goes to the brain."""

    def __init__(self, actions: ActionRegistry) -> None:
        self._actions = actions

    async def route(self, text: str) -> Route:
        said = text.strip().lower()
        for action in self._actions.all():
            if said in (p.lower() for p in action.phrases):
                return FastAction(action=action.name, score=1.0)
        return ToBrain()
