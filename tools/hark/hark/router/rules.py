"""Rules router: fixed commands to a named action, everything else to the brain (D4).

Pattern: Strategy (one ``Router``; a local model can replace it later).

Steps per utterance:

1. Normalise: lower case, drop punctuation, map synonyms ("pull up" →
   "open"), drop filler ("please", "can you", "the").
2. Veto: a destructive or negating word ("delete", "don't") that the
   phrase itself doesn't contain sends the turn to the brain, whatever the
   score. Those actions belong to the gate (R5), never to the fast path.
3. Score against every action's phrases: the max of token-set overlap
   (Jaccard: shared words / all words) and ``difflib.SequenceMatcher``
   ratio (character similarity, which forgives "lab" for "labs").
4. Best score at or above the threshold, and no other action also above
   it → ``FastAction``. Otherwise ``ToBrain`` carrying the best score.

Threshold 0.85 (D4 open question, kept after the near-miss tests): every
near miss in ``tests/test_router.py`` scores ≤ 0.82 and every rephrasing
that should be fast scores ≥ 0.89. The closest near miss is "open labs
github issues" (0.82): opening the repo instead would be a wrong action.
Jaccard is symmetric on purpose: extra words ("open labs and delete the
build") lower the score instead of being ignored, as a containment
measure would.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from hark.ports import ActionRegistry, FastAction, Route, ToBrain

THRESHOLD = 0.85

# Multi-word entries first: replacements run in order.
SYNONYMS: tuple[tuple[str, str], ...] = (
    ("pull up", "open"),
    ("bring up", "open"),
    ("show me", "open"),
    ("go to", "open"),
    ("take me to", "open"),
    ("launch", "open"),
    ("git hub", "github"),
)

FILLER: tuple[str, ...] = (
    "go ahead and",
    "i want to",
    "i would like to",
    "id like to",
    "can you",
    "could you",
    "would you",
    "will you",
    "for me",
    "please",
    "hey",
    "just",
    "the",
    "my",
    "a",
    "up",
)

# Never on the fast path (R5 belongs to the gate), nor when negated.
VETO = frozenset(
    {
        "delete", "remove", "rm", "erase", "wipe", "drop", "kill", "quit",
        "close", "push", "publish", "send", "commit", "deploy", "reset",
        "dont", "not", "never", "stop", "cancel", "no",
    }
)  # fmt: skip

_PUNCT = re.compile(r"[^\w\s]")


def _replace_words(text: str, old: str, new: str) -> str:
    return re.sub(rf"\b{re.escape(old)}\b", new, text)


def normalise(text: str) -> str:
    said = _PUNCT.sub("", text.lower())  # "don't" → "dont", "labs." → "labs"
    said = " ".join(said.split())
    for old, new in SYNONYMS:
        said = _replace_words(said, old, new)
    for word in FILLER:
        said = _replace_words(said, word, "")
    return " ".join(said.split())


def score(said: str, phrase: str) -> float:
    """Similarity of two normalised strings, 0..1."""
    a, b = set(said.split()), set(phrase.split())
    jaccard = len(a & b) / len(a | b) if a | b else 0.0
    return max(jaccard, SequenceMatcher(None, said, phrase).ratio())


class RulesRouter:
    def __init__(self, actions: ActionRegistry, threshold: float = THRESHOLD) -> None:
        self.threshold = threshold
        # Actions are fixed once loaded, so normalise their phrases once.
        self._phrases = [
            (action.name, normalise(p)) for action in actions.all() for p in action.phrases
        ]

    async def route(self, text: str) -> Route:
        said = normalise(text)
        words = set(said.split())
        seen = 0.0  # best score of any phrase, vetoed or not; ToBrain logs it
        best: dict[str, float] = {}  # action name → its best eligible phrase score
        for name, phrase in self._phrases:
            s = score(said, phrase)
            seen = max(seen, s)
            if not VETO & (words - set(phrase.split())):
                best[name] = max(best.get(name, 0.0), s)

        ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)
        if not ranked or ranked[0][1] < self.threshold:
            return ToBrain(score=seen)
        if len(ranked) > 1 and ranked[1][1] >= self.threshold:
            return ToBrain(score=seen)  # two actions fit: ambiguous, ask the brain
        return FastAction(action=ranked[0][0], score=ranked[0][1])
