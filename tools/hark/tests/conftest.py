"""Hardware tests (mic, speaker, local servers) are skipped unless asked for.

    uv run pytest --hardware      # or HARK_HARDWARE=1 uv run pytest
"""

from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--hardware", action="store_true", help="run tests that need audio hardware")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "hardware: needs a mic, speaker or local speech servers")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--hardware") or os.environ.get("HARK_HARDWARE") == "1":
        return
    skip = pytest.mark.skip(reason="hardware test: run with --hardware")
    for item in items:
        if "hardware" in item.keywords:
            item.add_marker(skip)
