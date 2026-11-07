"""Action registry and OpenResource (R4). ``open`` is mocked; nothing launches."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path

import pytest

from hark import ports
from hark.actions import OpenResource, Registry, load_resources
from hark.stubs import StubAction

EXAMPLE = Path(__file__).parent.parent / "examples" / "actions.toml"


class FakeOpener:
    def __init__(self, code: int = 0) -> None:
        self.code = code
        self.calls: list[list[str]] = []

    async def __call__(self, argv: Sequence[str]) -> int:
        self.calls.append(list(argv))
        return self.code


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "actions.toml"
    path.write_text(text)
    return path


def test_adapters_satisfy_ports():
    registry = load_resources(EXAMPLE, opener=FakeOpener())
    assert isinstance(registry, ports.ActionRegistry)
    for action in registry.all():
        assert isinstance(action, ports.Action)


def test_example_config_loads_url_app_and_path():
    registry = load_resources(EXAMPLE, opener=FakeOpener())
    argv = {a.name: a.argv for a in registry.all()}
    assert argv["project_github"] == ["open", "https://github.com/example-user/example-repo"]
    assert argv["calendar"] == ["open", "-a", "Calendar"]
    assert argv["downloads"] == ["open", str(Path("~/Downloads").expanduser())]


def test_run_calls_open_and_confirms():
    opener = FakeOpener()
    action = OpenResource(
        "labs_github", ["open labs github"], ["open", "https://example.com"],
        spoken="the labs GitHub page", opener=opener,
    )  # fmt: skip
    assert asyncio.run(action.run({})) == "Opening the labs GitHub page."
    assert opener.calls == [["open", "https://example.com"]]


def test_run_reports_failure():
    action = OpenResource("x", ["open x"], ["open", "-a", "Nope"], opener=FakeOpener(code=1))
    assert asyncio.run(action.run({})) == "Couldn't open x."


def test_registry_lookup():
    a = StubAction("a", ["open a"])
    registry = Registry([a])
    assert registry.get("a") is a
    assert registry.all() == [a]
    with pytest.raises(KeyError):
        registry.get("missing")


def test_registry_rejects_duplicates_and_empty_phrases():
    with pytest.raises(ValueError, match="duplicate"):
        Registry([StubAction("a", ["x"]), StubAction("a", ["y"])])
    with pytest.raises(ValueError, match="no phrases"):
        Registry([StubAction("a", [])])


@pytest.mark.parametrize(
    "entry, error",
    [
        ('url = "https://a.example"\napp = "Safari"', "exactly one"),
        ("", "exactly one"),
        ('url = "file:///etc/passwd"', "http"),
        ('app = ""', "non-empty"),
    ],
)
def test_bad_config_is_rejected(tmp_path, entry, error):
    path = write(tmp_path, f'[[resource]]\nname = "x"\nphrases = ["open x"]\n{entry}\n')
    with pytest.raises(ValueError, match=error):
        load_resources(path, opener=FakeOpener())


def test_phrases_must_be_strings(tmp_path):
    path = write(tmp_path, '[[resource]]\nname = "x"\nphrases = "open x"\nurl = "https://x.example"\n')
    with pytest.raises(ValueError, match="phrases"):
        load_resources(path, opener=FakeOpener())
