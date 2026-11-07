"""Stand-in for ``claude -p`` in stream-JSON mode, replaying a recorded run.

Events come from tests/fixtures/claude_stream.jsonl with @TEXT@ and
@SESSION@ filled in. The prompt picks the behaviour:

    die           write a partial delta, then exit mid-turn
    hang          never answer
    pid           answer with this process's pid
    unknown       add event types the parser has never seen
    error         end with an is_error result
    tool:CMD      ask the PreToolUse hook from --settings about Bash(CMD), as
                  Claude Code does, then answer "Ran CMD." or the block reason
    anything else answer with the prompt text itself

Set FAKE_ARGV_FILE to record the argv, FAKE_CWD_FILE the working directory.
"""

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "claude_stream.jsonl"
SESSION = str(uuid.uuid4())


def emit(line: str) -> None:
    sys.stdout.write(line.rstrip("\n") + "\n")
    sys.stdout.flush()


def replay(text: str, *, unknown: bool = False, error: bool = False) -> None:
    for raw in FIXTURE.read_text().splitlines():
        event = json.loads(raw.replace("@SESSION@", SESSION).replace("@TEXT@", "@T@"))

        def fill(node):
            if isinstance(node, str):
                return node.replace("@T@", text)
            if isinstance(node, list):
                return [fill(n) for n in node]
            if isinstance(node, dict):
                return {k: fill(v) for k, v in node.items()}
            return node

        event = fill(event)
        if error and event["type"] == "result":
            event["is_error"] = True
        emit(json.dumps(event))
        if unknown and event.get("subtype") == "init":
            emit(json.dumps({"type": "future_thing", "payload": [1, 2, 3]}))
            emit("this line is not json at all")
            emit(json.dumps({"type": "stream_event", "event": {"type": "brand_new"}}))


def run_hook(command: str) -> str:
    """Run the settings file's PreToolUse hook the way Claude Code does."""
    settings = json.loads(Path(sys.argv[sys.argv.index("--settings") + 1]).read_text())
    hook = settings["hooks"]["PreToolUse"][0]["hooks"][0]
    call = {"tool_name": "Bash", "tool_input": {"command": command}, "session_id": SESSION}
    try:
        done = subprocess.run(
            hook["command"], shell=True, input=json.dumps(call), capture_output=True,
            text=True, timeout=hook["timeout"],
        )  # fmt: skip
    except subprocess.TimeoutExpired:
        return "Blocked: the hook timed out."
    if done.returncode == 0 and '"allow"' in done.stdout:
        return f"Ran {command}."
    return done.stderr.strip() or "Blocked."


def main() -> None:
    if path := os.environ.get("FAKE_ARGV_FILE"):
        Path(path).write_text(json.dumps(sys.argv[1:]))
    if path := os.environ.get("FAKE_CWD_FILE"):
        Path(path).write_text(os.getcwd())
    for line in sys.stdin:
        message = json.loads(line)
        prompt = message["message"]["content"]
        if prompt == "die":
            emit(json.dumps({"type": "system", "subtype": "init", "session_id": SESSION}))
            os._exit(1)
        elif prompt == "hang":
            time.sleep(3600)
        elif prompt == "pid":
            replay(str(os.getpid()))
        elif prompt == "unknown":
            replay("fine.", unknown=True)
        elif prompt.startswith("tool:"):
            replay(run_hook(prompt.removeprefix("tool:")))
        elif prompt == "error":
            replay("boom", error=True)
        else:
            replay(prompt)


if __name__ == "__main__":
    main()
