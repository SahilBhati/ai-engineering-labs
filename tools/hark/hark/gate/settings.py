"""The Claude Code hook settings: the whole interface between lane C and D."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

CONFIRM_WINDOW_S = 10  # total time the user has to answer (GateConfig.window_s)
TIMEOUT_MARGIN_S = 5  # speaking the question, plus slack


def hook_timeout(window_s: float = CONFIRM_WINDOW_S) -> int:
    """Hook timeout just above the confirmation window, not the 600 s default."""
    return int(window_s) + TIMEOUT_MARGIN_S


def hook_settings(hook_path: str | Path, timeout: int | None = None) -> dict[str, Any]:
    """The ``--settings`` content: a fail-closed PreToolUse hook on every tool.

    ``onFailure: block`` is what makes a missing script or a timeout block the
    call; without it both let it through (LAB-01 runs 02-04). The hook is told
    to give up a second before Claude Code would kill it, so it can print its
    own reason.
    """
    timeout = hook_timeout() if timeout is None else timeout
    if timeout < 2:
        raise ValueError("timeout must be at least 2 seconds")
    command = f"{shlex.quote(str(hook_path))} --timeout {timeout - 1}"
    return {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": command,
                            "timeout": timeout,
                            "onFailure": "block",
                        }
                    ],
                }
            ]
        }
    }
