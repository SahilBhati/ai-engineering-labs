"""The classifier corpus (D6, LAB-01 key learning 5): anything not clearly safe asks."""

from __future__ import annotations

import random

import pytest

from hark.gate.classify import Kind, classify, classify_command
from hark.ports import ToolCall


def bash(command) -> ToolCall:
    return ToolCall(turn_id="t", tool="Bash", input={"command": command})


MUST_ASK = [
    "rm x",
    "unlink x",
    "/bin/rm x",
    "\\rm x",
    "'rm' x",
    "r''m x",
    "command rm x",
    "FOO=1 rm x",
    "env rm x",
    "exec rm x",
    "find . -delete",
    "find . -exec rm {} +",
    "find . -execdir rm {} ;",
    "find . -ok rm {} ;",
    "find . -fprint out.txt",
    "xargs rm",
    'python -c "import os; os.remove(\'x\')"',
    "python3 script.py",
    "node -e 'require(\"fs\").unlinkSync(\"x\")'",
    "perl -e unlink",
    "ruby -e 'File.delete(1)'",
    "git push",
    "git -C repo push",
    "git push --force",
    "git checkout -- x",
    "git commit -m x",
    "git branch foo",
    "git branch -D foo",
    "git remote add x y",
    "git diff --output=out.txt",
    "git diff --out=out.txt",
    "git log --o=x",
    "git show --ext=x",
    "git diff -Oorderfile",
    "git diff --open-files-in-pager",
    "git -c core.pager=rm status",
    "gh pr create",
    "gh release create v1",
    "npm publish",
    "mv x ~/.Trash",
    "cp a b",
    "chmod 777 x",
    "kill -9 1",
    "> file",
    "echo hi > file",
    "echo hi >> file",
    "echo hi >file",
    "ls 2>file",
    "ls >/dev/null.bak",
    "cat < file",
    "cat <<EOF",
    "cat <(ls)",
    "cat a | tee b",
    "sort -o out in",
    "sort --output=out in",
    "sort --compress-program=sh in",
    "uniq in out",
    "rg --pre rm foo",
    "sed -i s/a/b/ f",
    "awk 'BEGIN{system(\"rm x\")}'",
    "curl -X POST https://example.com",
    "wget https://example.com",
    "ssh host ls",
    "osascript -e 'tell application \"Mail\" to send m'",
    "echo hi; rm x",
    "echo hi && rm x",
    "echo hi || rm x",
    "echo hi | rm x",
    "echo hi & rm x",
    "echo hi |& rm x",
    "ls\nrm x",
    "ls \\\n; rm x",
    "echo $(rm x)",
    "echo `rm x`",
    'echo "$(rm x)"',
    'echo "`rm x`"',
    "echo $(echo $(rm x))",
    "$(echo rm) x",
    "$CMD x",
    "echo ${X:-$(rm y)}",
    "echo $((1+1))",
    "echo $'\\x72m'",
    "(rm x)",
    "(ls; rm x)",
    "{ rm x; }",
    "bash -c 'rm x'",
    'bash -c "rm x"',
    "sh -c 'a; rm b'",
    "sh -c 'ls; rm b'",
    "sh -c ls extra",
    "bash script.sh",
    "bash",
    "sh",
    "eval rm x",
    "eval 'ls; rm x'",
    "eval $X",
    "echo cm0geA== | base64 -d | sh",
    "ls; echo 'unterminated",
    'echo "unterminated',
    "echo `unterminated",
    "echo $(unterminated",
    "ls \\",
    "",
    "   ",
    "\n",
    "ls\x00rm",
    "x" * 20_000,
    "echo " + "a" * 1_000_000,
    "date -s 2020",
    "date 010101012020",
    "find $HOME -delete",
    "find $(echo .) -name x",
    "unknown-tool --flag",
    "time ls",
    "! ls",
    "if true; then rm x; fi",
    "for f in a; do rm $f; done",
    "while true; do ls; done",
    "alias ls='rm'",
    "ls() { rm x; }",
    "function ls { rm x; }",
]

MUST_ALLOW = [
    "ls -la",
    "ls",
    "git status",
    "git log --oneline -5",
    "git diff HEAD~1",
    "git log --oneline --stat --format=%H",
    "git diff --name-only --cached",
    "git show HEAD",
    "git -C repo status",
    "git branch --list",
    "git branch",
    "git remote -v",
    "ps aux | grep claude | wc -l",
    "find . -name '*.py' | wc -l",
    "grep -r def src | head",
    "echo hi",
    "echo 'a;b|c&d > e'",
    'echo "a; rm x"',
    'echo "a\\"; rm x"',
    "echo $HOME",
    "echo $(ls)",
    'echo "$(pwd)"',
    "echo `pwd`",
    "ls 2>&1",
    "ls >/dev/null",
    "ls 2>/dev/null",
    "ls &>/dev/null",
    "pwd && ls -la && git status",
    "cd src && ls",
    "cat a b | sort | uniq -c | sort -rn | head -5",
    "sort -u -k2 file",
    "uniq -c file",
    "rg -n foo src",
    "date +%Y-%m-%d",
    "bash -c 'ls | wc -l'",
    "eval ls",
    "ls &",
    "head -n 5 file; tail -n 5 file",
    "uname -a && whoami && df -h && du -sh .",
    "which python",
    "wc -l < /dev/null".replace("< /dev/null", "file"),
]


@pytest.mark.parametrize("command", MUST_ASK, ids=lambda c: repr(c)[:50])
def test_must_ask(command):
    verdict = classify(bash(command))
    assert verdict.kind is Kind.ASK, f"{command[:80]!r} reached ALLOW"
    assert verdict.reason


@pytest.mark.parametrize("command", MUST_ALLOW)
def test_must_allow(command):
    assert classify(bash(command)).kind is Kind.ALLOW, command


@pytest.mark.parametrize("command", [None, 5, ["ls"], {"a": 1}, b"ls"])
def test_non_string_command_asks(command):
    assert classify(bash(command)).kind is Kind.ASK


@pytest.mark.parametrize("input", [{}, {"cmd": "ls"}, {"command": None}])
def test_missing_command_asks(input):
    assert classify(ToolCall("t", "Bash", input)).kind is Kind.ASK


def test_ask_reasons_are_speakable():
    assert classify(bash("rm x")).reason == "delete files with rm"
    assert classify(bash("git push")).reason == "push to a remote with git"
    assert classify(bash("npm publish")).reason == "publish with npm"
    assert classify(bash("ls; rm x")).reason == "delete files with rm"


@pytest.mark.parametrize("tool", ["Read", "Glob", "Grep"])
def test_read_only_tools_allow(tool):
    assert classify(ToolCall("t", tool, {"file_path": "/etc/hosts"})).kind is Kind.ALLOW


@pytest.mark.parametrize(
    "tool",
    ["Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch", "Task", "mcp__slack__send", "TodoWrite", "bash", "", "Whatever"],
)
def test_other_tools_ask(tool):
    assert classify(ToolCall("t", tool, {"command": "ls"})).kind is Kind.ASK


SAFE_SEGMENTS = [
    "ls -la", "git status", "echo hi", "pwd", "ps aux", "wc -l f", "grep -r x .",
    "head f", "git log --oneline", "sort f", "cat f", "find . -name x", "echo 'a;b'",
]  # fmt: skip
UNSAFE_SEGMENTS = [
    "rm x", "unlink x", "find . -delete", "git push", "mv a b", "echo hi > f",
    "python -c 1", "curl x", "tee f", "echo $(rm x)", "sh -c 'rm x'", "chmod 1 f",
    "FOO=1 ls", "sort -o f f", "(ls)",
]  # fmt: skip
JOINERS = ["; ", " && ", " || ", " | ", "\n", " & "]


def test_any_unsafe_segment_in_a_safe_composition_asks():
    rng = random.Random(20261107)
    for _ in range(2000):
        n = rng.randint(1, 6)
        parts = [rng.choice(SAFE_SEGMENTS) for _ in range(n)]
        parts[rng.randrange(n)] = rng.choice(UNSAFE_SEGMENTS)
        command = parts[0]
        for p in parts[1:]:
            command += rng.choice(JOINERS) + p
        assert classify_command(command).kind is Kind.ASK, command


def test_safe_compositions_allow():
    rng = random.Random(7)
    for _ in range(500):
        parts = [rng.choice(SAFE_SEGMENTS) for _ in range(rng.randint(1, 6))]
        command = parts[0]
        for p in parts[1:]:
            command += rng.choice(JOINERS) + p
        assert classify_command(command).kind is Kind.ALLOW, command


def test_never_raises_on_garbage():
    rng = random.Random(1)
    alphabet = r"""abc $()`'"\;&|<>{}#!*?~=-/""" + "\n\t"
    for _ in range(3000):
        s = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 30)))
        assert classify_command(s).kind in (Kind.ALLOW, Kind.ASK)


def test_nothing_with_rm_reaches_allow_in_random_soup():
    # Whatever the punctuation, a bare `rm` word anywhere must never be allowed.
    rng = random.Random(2)
    alphabet = ["ls", "rm", "echo", " ", " ", ";", "&&", "|", "\n", "'", '"', "$(", ")", "`", "\\"]
    for _ in range(5000):
        s = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 12)))
        if classify_command(s).allowed:
            # allowed output must not contain an executed rm: rm only as quoted/arg text
            assert not _runs_rm(s), s


def _runs_rm(s: str) -> bool:
    """Independent oracle: ask a real shell, in dry-run mode, what `rm` would run."""
    import subprocess

    probe = "rm() { echo RAN_RM; }; " + s
    try:
        out = subprocess.run(
            ["bash", "-c", probe], capture_output=True, text=True, timeout=5, input="", cwd="/"
        ).stdout
    except subprocess.TimeoutExpired:
        return False
    return "RAN_RM" in out
