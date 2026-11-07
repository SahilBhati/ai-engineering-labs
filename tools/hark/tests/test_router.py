"""Rules router (D4): R4 phrases route fast; near misses go to the brain."""

from __future__ import annotations

import asyncio
import time

import pytest

from hark import ports
from hark.actions import Registry
from hark.ports import FastAction, ToBrain
from hark.router import THRESHOLD, RulesRouter, normalise
from hark.stubs import StubAction


def make_router() -> RulesRouter:
    registry = Registry(
        [
            StubAction(
                "labs_github",
                ["open my AI Engineering Labs GitHub page", "open labs github"],
            ),
            StubAction("labs_site", ["open labs"]),
            StubAction("calendar", ["open calendar"]),
            StubAction("downloads", ["open downloads"]),
        ]
    )
    return RulesRouter(registry)


def route(text: str):
    return asyncio.run(make_router().route(text))


def test_router_satisfies_port():
    assert isinstance(make_router(), ports.Router)


@pytest.mark.parametrize(
    "said, normalised",
    [
        ("Please open the AI Engineering Labs page.", "open ai engineering labs page"),
        ("Can you pull up my calendar?", "open calendar"),
        ("Hey, launch git hub", "open github"),
        ("Don't open labs!", "dont open labs"),
    ],
)
def test_normalise(said, normalised):
    assert normalise(said) == normalised


@pytest.mark.parametrize(
    "said, action",
    [
        # R4 as written, and close rephrasings
        ("Open my AI Engineering Labs GitHub page.", "labs_github"),
        ("Please open the AI engineering labs github page", "labs_github"),
        ("Can you pull up my AI Engineering Labs GitHub page?", "labs_github"),
        ("open my AI Engineering Labs git hub page", "labs_github"),
        ("open AI engineering labs on GitHub", "labs_github"),
        ("launch labs github", "labs_github"),
        ("open lab", "labs_site"),  # speech-to-text dropped the s
        ("Open labs.", "labs_site"),
        ("could you open my calendar for me", "calendar"),
    ],
)
def test_fast_path(said, action):
    result = route(said)
    assert isinstance(result, FastAction), result
    assert result.action == action
    assert result.score >= THRESHOLD


@pytest.mark.parametrize(
    "said",
    [
        # near misses: close to a phrase, but the fast action would be wrong
        "open labs and delete the build",
        "open labs github issues",
        "open labs website",
        "open the labs lesson three page",
        "close labs",
        "don't open labs",
        "push labs to github",
        "open slack",
        "open",
        # unrelated
        "what's on my calendar today",
        "why is the build failing",
        "open a new terminal and run the tests",
        "",
    ],
)
def test_brain_path(said):
    result = route(said)
    assert isinstance(result, ToBrain), result
    assert result.score < THRESHOLD


def test_to_brain_carries_best_score_for_the_miss_rate():
    result = route("open labs website")
    assert isinstance(result, ToBrain)
    assert 0.5 < result.score < THRESHOLD


def test_veto_word_beats_a_perfect_phrase_match():
    # Every word but "delete" matches; still never the fast path.
    assert isinstance(route("delete open labs"), ToBrain)


def test_veto_word_allowed_when_the_phrase_has_it():
    registry = Registry([StubAction("stop_music", ["stop the music"])])
    result = asyncio.run(RulesRouter(registry).route("please stop the music"))
    assert result == FastAction(action="stop_music", score=1.0)


def test_two_actions_above_threshold_is_ambiguous():
    registry = Registry([StubAction("a", ["open notes"]), StubAction("b", ["open note"])])
    result = asyncio.run(RulesRouter(registry).route("open notes"))
    assert isinstance(result, ToBrain)
    assert result.score == 1.0


def test_route_is_under_10_ms():
    router = make_router()
    texts = ["Open my AI Engineering Labs GitHub page.", "open labs and delete the build"]

    async def time_all() -> float:
        worst = 0.0
        for _ in range(50):
            for text in texts:
                started = time.perf_counter()
                await router.route(text)
                worst = max(worst, time.perf_counter() - started)
        return worst

    assert asyncio.run(time_all()) < 0.010
