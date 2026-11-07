"""Hardware and live tests are skipped unless asked for.

    uv run pytest --hardware      # or HARK_HARDWARE=1 uv run pytest
    uv run pytest -m live         # drives the real `claude` CLI
"""

from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--hardware", action="store_true", help="run tests that need audio hardware")
    parser.addoption("--live", action="store_true", help="run tests that call the real claude CLI")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "hardware: needs a mic, speaker or local speech servers")
    config.addinivalue_line("markers", "live: runs the real claude CLI (uses the subscription)")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    run_hardware = config.getoption("--hardware") or os.environ.get("HARK_HARDWARE") == "1"
    markexpr = config.getoption("-m") or ""
    run_live = config.getoption("--live") or "live" in markexpr
    skip_hardware = pytest.mark.skip(reason="hardware test: run with --hardware")
    skip_live = pytest.mark.skip(reason="live test: run with -m live")
    for item in items:
        if "hardware" in item.keywords and not run_hardware:
            item.add_marker(skip_hardware)
        if "live" in item.keywords and not run_live:
            item.add_marker(skip_live)
