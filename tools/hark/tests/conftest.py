"""Hardware and live tests are skipped unless asked for.

    uv run pytest --hardware      # or HARK_HARDWARE=1 uv run pytest
    uv run pytest -m live         # drives the real `claude` CLI
"""

from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--hardware", action="store_true", help="run tests that need audio hardware")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "hardware: needs a mic, speaker or local speech servers")
    config.addinivalue_line("markers", "live: drives the real `claude` CLI; run with -m live")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if "live" not in (config.getoption("-m") or ""):
        skip_live = pytest.mark.skip(reason="live test: run with -m live (needs `claude`)")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)
    if config.getoption("--hardware") or os.environ.get("HARK_HARDWARE") == "1":
        return
    skip = pytest.mark.skip(reason="hardware test: run with --hardware")
    for item in items:
        if "hardware" in item.keywords:
            item.add_marker(skip)
