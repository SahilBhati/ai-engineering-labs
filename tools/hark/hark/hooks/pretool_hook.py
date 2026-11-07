#!/usr/bin/env python3
"""Claude Code PreToolUse hook: the enforcement point (D6).

Sends the tool call to Hark over a Unix socket and prints an allow only when
Hark answers a clear allow. Everything else exits 2, which blocks the call.

Standalone on purpose: standard library only and no ``hark`` import, because
it starts once per tool call and start-up counts.

    pretool_hook.py [--socket PATH] [--timeout SECONDS]

The socket comes from --socket, then $HARK_GATE_SOCKET, then
~/.config/hark/gate.sock. Wire format: one JSON line each way.
    request  {"tool_name": ..., "tool_input": {...}, "session_id": ...}
    reply    {"allow": true|false, "reason": "..."}
"""

import json
import os
import socket
import sys
import time

DEFAULT_SOCKET = os.path.join(os.path.expanduser("~"), ".config", "hark", "gate.sock")
DEFAULT_TIMEOUT = 14.0
MAX_REPLY_BYTES = 65536
BLOCK = 2


class Blocked(Exception):
    """Anything that must stop the call; the message is shown to the user."""


def parse_args(argv):
    sock = os.environ.get("HARK_GATE_SOCKET") or DEFAULT_SOCKET
    timeout = DEFAULT_TIMEOUT
    it = iter(argv)
    for arg in it:
        if arg == "--socket":
            sock = next(it)
        elif arg == "--timeout":
            timeout = float(next(it))
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    return sock, timeout


def read_request(stdin):
    raw = stdin.read()
    if not raw.strip():
        raise Blocked("Blocked: the tool call came with no details, so Hark could not check it.")
    try:
        data = json.loads(raw)
    except ValueError:
        raise Blocked("Blocked: the tool call was unreadable, so Hark could not check it.")
    if not isinstance(data, dict):
        raise Blocked("Blocked: the tool call was malformed, so Hark could not check it.")
    tool, tool_input = data.get("tool_name"), data.get("tool_input")
    if not isinstance(tool, str) or not isinstance(tool_input, dict):
        raise Blocked("Blocked: the tool call was malformed, so Hark could not check it.")
    session = data.get("session_id")
    return {
        "tool_name": tool,
        "tool_input": tool_input,
        "session_id": session if isinstance(session, str) else None,
    }


def ask_hark(request, path, timeout):
    deadline = time.monotonic() + timeout
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(path)
            s.sendall(json.dumps(request).encode() + b"\n")
            buf = b""
            while b"\n" not in buf:
                left = deadline - time.monotonic()
                if left <= 0:
                    raise socket.timeout
                s.settimeout(left)
                chunk = s.recv(4096)
                if not chunk:
                    raise Blocked("Blocked: Hark closed the connection without an answer.")
                buf += chunk
                if len(buf) > MAX_REPLY_BYTES:
                    raise Blocked("Blocked: Hark sent an answer that was too long.")
    except socket.timeout:
        raise Blocked("Blocked: Hark did not answer in time.")
    except OSError:
        raise Blocked("Blocked: Hark is not running, so the call was not checked.")
    try:
        reply = json.loads(buf.split(b"\n", 1)[0])
    except ValueError:
        raise Blocked("Blocked: Hark sent an answer I could not read.")
    if not isinstance(reply, dict) or not isinstance(reply.get("allow"), bool):
        raise Blocked("Blocked: Hark sent an answer I could not read.")
    reason = reply.get("reason")
    reason = reason if isinstance(reason, str) and reason else None
    if reply["allow"] is not True:
        raise Blocked(reason or "Blocked: Hark said no.")
    return reason or "Hark allowed it"


def main(argv, stdin):
    """Returns the allow JSON text; raises Blocked for everything else."""
    path, timeout = parse_args(argv)
    request = read_request(stdin)
    reason = ask_hark(request, path, timeout)
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": reason,
            }
        }
    )


def run():
    # One exit point per outcome: 0 only after an allow was printed in full.
    try:
        allow = main(sys.argv[1:], sys.stdin)
        sys.stdout.write(allow + "\n")
        sys.stdout.flush()
    except Blocked as e:
        message = str(e)
    except BaseException:
        message = "Blocked: Hark's safety hook hit an error, so the call was not checked."
    else:
        return 0
    try:
        sys.stderr.write(message + "\n")
        sys.stderr.flush()
    except BaseException:
        pass
    return BLOCK


if __name__ == "__main__":
    os._exit(run())
