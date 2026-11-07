"""Classifier: is a tool call clearly safe, or does it need a spoken yes? (R5, D6)

``classify`` is an allow-list. A call is ``ALLOW`` only if every part of it is
recognised as read-only; everything else, and everything that cannot be fully
parsed, is ``ASK``. The rules never decide "deny": only the user's spoken no,
silence, or a gate failure deny. A deny-list leaks (LAB-01: after ``rm`` was
blocked the model offered ``unlink``).

Bash commands are tokenised by a small shell lexer that understands quotes,
escapes, ``$( )`` and backticks; anything it does not understand (parentheses,
``${ }``, ``$'..'``, heredocs, unknown redirections) makes the answer ``ASK``.
Pure functions, no I/O.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from hark.ports import ToolCall

MAX_COMMAND_CHARS = 10_000
MAX_DEPTH = 6  # nested substitutions / bash -c payloads


class Kind(StrEnum):
    ALLOW = "ALLOW"
    ASK = "ASK"


@dataclass(frozen=True)
class Verdict:
    kind: Kind
    reason: str  # for ASK: spoken after "Allow:", e.g. "delete files with rm"

    @property
    def allowed(self) -> bool:
        return self.kind is Kind.ALLOW


def _allow(reason: str) -> Verdict:
    return Verdict(Kind.ALLOW, reason)


def _ask(reason: str) -> Verdict:
    return Verdict(Kind.ASK, reason)


UNCHECKED = "run a command I cannot check"
READ_ONLY_TOOLS = frozenset({"Read", "Glob", "Grep"})
TOOL_REASONS = {
    "Write": "write a file",
    "Edit": "edit a file",
    "NotebookEdit": "edit a notebook",
    "WebFetch": "fetch a web page",
    "WebSearch": "search the web",
    "Task": "start a sub agent",
    "Agent": "start a sub agent",
}


def classify(call: ToolCall) -> Verdict:
    """Never raises: any surprise is ``ASK``."""
    try:
        return _classify(call)
    except Exception:  # noqa: BLE001 — fail closed
        return _ask(UNCHECKED)


def _classify(call: ToolCall) -> Verdict:
    tool = call.tool
    if tool in READ_ONLY_TOOLS:
        return _allow("read-only tool")
    if tool == "Bash":
        command = call.input.get("command") if isinstance(call.input, dict) else None
        if not isinstance(command, str):
            return _ask(UNCHECKED)
        return classify_command(command)
    if tool in TOOL_REASONS:
        return _ask(TOOL_REASONS[tool])
    if isinstance(tool, str) and tool.startswith("mcp__"):
        return _ask("use an external tool")
    return _ask("use a tool I do not know")


# --- shell lexer -----------------------------------------------------------


class _Unsupported(Exception):
    """The command uses syntax this parser does not model; the answer is ASK."""

    def __init__(self, reason: str = UNCHECKED) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class _Word:
    text: str = ""
    quoted: bool = False  # any quote or backslash was used
    dynamic: bool = False  # contains $var or a command substitution
    redirect: bool = False  # contains an unquoted < or >
    started: bool = False


SEPARATORS = ";|&\n"
SIMPLE_REDIRECT = re.compile(r"(?:[12]?>/dev/null|&>/dev/null|2>&1)")


def _closing_paren(s: str, i: int) -> int:
    """Index of the ``)`` matching a ``$(`` whose body starts at ``i``."""
    depth = 1
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "'":
            j = s.find("'", i + 1)
            if j < 0:
                raise _Unsupported
            i = j + 1
            continue
        if c == '"':
            i = _closing_quote(s, i + 1) + 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise _Unsupported


def _closing_quote(s: str, i: int) -> int:
    """Index of the ``"`` closing a double-quoted string whose body starts at ``i``."""
    while i < len(s):
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == '"':
            return i
        if c == "$" and s.startswith("$(", i):
            i = _closing_paren(s, i + 2) + 1
            continue
        if c == "`":
            j = s.find("`", i + 1)
            if j < 0:
                raise _Unsupported
            i = j + 1
            continue
        i += 1
    raise _Unsupported


def _substitution(body: str, depth: int) -> None:
    """A substitution is fine only if what it runs is itself clearly safe."""
    verdict = classify_command(body, depth + 1)
    if not verdict.allowed:
        raise _Unsupported(verdict.reason)


def _dollar(s: str, i: int, word: _Word, depth: int, in_double: bool) -> int:
    """Handle ``$`` at ``s[i]``; returns the index after what was consumed."""
    nxt = s[i + 1 : i + 2]
    if s.startswith("$((", i) or nxt == "{" or (nxt in ("'", '"') and not in_double):
        raise _Unsupported
    if nxt == "(":
        end = _closing_paren(s, i + 2)
        _substitution(s[i + 2 : end], depth)
        word.dynamic = True
        return end + 1
    if nxt.isalnum() or nxt in ("_", "?", "$", "!", "#", "@", "*", "-"):
        word.dynamic = True
        return i + 2
    word.text += "$"  # a lone $ is a literal dollar
    return i + 1


def _backtick(s: str, i: int, word: _Word, depth: int) -> int:
    j = s.find("`", i + 1)
    if j < 0:
        raise _Unsupported
    body = s[i + 1 : j]
    if "\\" in body:
        raise _Unsupported
    _substitution(body, depth)
    word.dynamic = True
    return j + 1


def _double_quoted(s: str, i: int, word: _Word, depth: int) -> int:
    """``s[i]`` is the opening ``"``; returns the index after the closing one."""
    word.quoted = word.started = True
    i += 1
    while i < len(s):
        c = s[i]
        if c == '"':
            return i + 1
        if c == "\\":
            if i + 1 >= len(s):
                raise _Unsupported
            nxt = s[i + 1]
            word.text += nxt if nxt in '$`"\\' else "\\" + nxt
            i += 2
        elif c == "$":
            i = _dollar(s, i, word, depth, in_double=True)
        elif c == "`":
            i = _backtick(s, i, word, depth)
        else:
            word.text += c
            i += 1
    raise _Unsupported  # unbalanced quote


def split_commands(s: str, depth: int = 0) -> list[list[_Word]]:
    """Split a command line into simple commands, each a list of words."""
    if depth > MAX_DEPTH:
        raise _Unsupported
    commands: list[list[_Word]] = [[]]
    word = _Word()

    def end_word() -> None:
        nonlocal word
        if word.started:
            commands[-1].append(word)
        word = _Word()

    i = 0
    while i < len(s):
        c = s[i]
        if c in " \t":
            end_word()
            i += 1
        elif c == "\n" or c == ";" or c == "|":
            end_word()
            commands.append([])
            i += 1
        elif c == "&":
            if (word.started and word.text.endswith(">")) or s.startswith("&>", i):
                word.text += c  # part of 2>&1 or &>
                word.started = True
                i += 1
            else:
                end_word()
                commands.append([])
                i += 1
        elif c in "<>":
            word.redirect = word.started = True
            word.text += c
            i += 1
        elif c in "()":
            raise _Unsupported
        elif c == "\\":
            if i + 1 >= len(s):
                raise _Unsupported
            if s[i + 1] == "\n":  # line continuation
                i += 2
                continue
            word.text += s[i + 1]
            word.quoted = word.started = True
            i += 2
        elif c == "'":
            j = s.find("'", i + 1)
            if j < 0:
                raise _Unsupported
            word.text += s[i + 1 : j]
            word.quoted = word.started = True
            i = j + 1
        elif c == '"':
            i = _double_quoted(s, i, word, depth)
        elif c == "$":
            word.started = True
            i = _dollar(s, i, word, depth, in_double=False)
        elif c == "`":
            word.started = True
            i = _backtick(s, i, word, depth)
        else:
            word.text += c
            word.started = True
            i += 1
    end_word()
    return [cmd for cmd in commands if cmd]


# --- per-program rules -------------------------------------------------------

# Each checker gets the argument words and returns None if the arguments are
# read-only, or a spoken reason if they are not.
type Checker = Callable[[list[_Word]], str | None]


def _plain(_args: list[_Word]) -> str | None:
    return None


def _literal(args: list[_Word]) -> list[str] | None:
    return None if any(a.dynamic for a in args) else [a.text for a in args]


def _check_find(args: list[_Word]) -> str | None:
    texts = _literal(args)
    if texts is None:
        return "run find with arguments I cannot check"
    bad = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0", "-fprintf", "-fls"}
    if bad & set(texts):
        return "delete or run commands with find"
    return None


def _check_rg(args: list[_Word]) -> str | None:
    texts = _literal(args)
    if texts is None:
        return "run ripgrep with arguments I cannot check"
    if any(t.startswith(("--pre", "--hostname")) for t in texts):
        return "run a program through ripgrep"
    return None


_SORT_FLAGS = re.compile(r"-[bdfghiMnrRsuVz]+|-t.|-k\d+(?:,\d+)?[bdfghiMnrV]*")
_SORT_LONG = {
    "--reverse", "--numeric-sort", "--unique", "--ignore-case", "--stable",
    "--human-numeric-sort", "--version-sort", "--ignore-leading-blanks",
    "--dictionary-order", "--month-sort", "--general-numeric-sort",
}  # fmt: skip


def _check_sort(args: list[_Word]) -> str | None:
    texts = _literal(args)
    if texts is None:
        return "run sort with arguments I cannot check"
    for t in texts:
        if t.startswith("-") and t != "-":
            if not (_SORT_FLAGS.fullmatch(t) or t in _SORT_LONG):
                return "write a file with sort"
    return None


def _check_uniq(args: list[_Word]) -> str | None:
    texts = _literal(args)
    if texts is None:
        return "run uniq with arguments I cannot check"
    positional = [t for t in texts if not t.startswith("-") or t == "-"]
    flags = [t for t in texts if t.startswith("-") and t != "-"]
    if len(positional) > 1 or not all(re.fullmatch(r"-[cdui]+", f) for f in flags):
        return "write a file with uniq"
    return None


def _check_date(args: list[_Word]) -> str | None:
    texts = _literal(args)
    if texts is None or not all(t == "-u" or t.startswith("+") for t in texts):
        return "change the system date"
    return None


# Long flags that write a file or run a program. git accepts any unique prefix
# of a long flag (--out=x is --output=x), so a prefix of one of these is unsafe.
_GIT_UNSAFE_LONG = ("--output", "--ext-diff", "--open-files-in-pager")


def _git_flag_unsafe(arg: str) -> bool:
    if arg.startswith("--"):
        flag = arg.split("=", 1)[0]
        return any(w.startswith(flag) for w in _GIT_UNSAFE_LONG)
    return arg.startswith("-O")  # -O<orderfile> / -O<pager>


_BRANCH_FLAGS = {"--list", "-l", "-a", "--all", "-r", "--remotes", "-v", "-vv", "--verbose", "--show-current"}


def _check_git(args: list[_Word]) -> str | None:
    texts = _literal(args)
    if texts is None:
        return "run git with arguments I cannot check"
    if texts[:1] == ["-C"] and len(texts) >= 2:
        texts = texts[2:]
    if not texts:
        return "run git"
    sub, rest = texts[0], texts[1:]
    if sub in ("status", "log", "diff", "show"):
        if any(_git_flag_unsafe(t) for t in rest):
            return f"write a file with git {sub}"
        return None
    if sub == "branch":
        if all(t in _BRANCH_FLAGS or (not t.startswith("-") and "--list" in rest) for t in rest):
            return None
        return "change git branches"
    if sub == "remote" and rest in ([], ["-v"], ["--verbose"]):
        return None
    if sub == "push":
        return "push to a remote with git"
    return f"run git {sub}" if sub.isalpha() else "run git"


SAFE_PROGRAMS: dict[str, Checker] = {
    **{
        name: _plain
        for name in (
            "ls cat head tail wc grep egrep fgrep ps pgrep pwd echo which whoami df du uname "
            "cut tr basename dirname id nl tac rev stat true false cd"
        ).split()
    },
    "find": _check_find,
    "rg": _check_rg,
    "sort": _check_sort,
    "uniq": _check_uniq,
    "date": _check_date,
    "git": _check_git,
}

SHELLS = frozenset({"bash", "sh", "zsh", "dash"})

# What to say for commands that are not on the safe list. Anything missing here
# is spoken as "run <name>".
SPOKEN: dict[str, str] = {
    **dict.fromkeys(("rm", "unlink", "rmdir", "shred", "trash"), "delete files with {}"),
    **dict.fromkeys(("mv", "cp", "ln", "rsync", "install"), "move or copy files with {}"),
    **dict.fromkeys(("chmod", "chown", "chgrp"), "change file permissions with {}"),
    **dict.fromkeys(("kill", "pkill", "killall"), "stop processes with {}"),
    **dict.fromkeys(("curl", "wget", "ssh", "scp", "nc", "ftp"), "use the network with {}"),
    **dict.fromkeys(
        ("python", "python3", "node", "perl", "ruby", "osascript", "php", "deno", "bun", "lua"),
        "run a script with {}",
    ),
    **dict.fromkeys(("npm", "pnpm", "yarn", "pip", "pip3", "uv", "brew", "cargo", "gem"), "run the package manager {}"),
    **dict.fromkeys(("sh", "bash", "zsh", "eval", "exec", "sudo", "xargs", "env", "command"), "run commands through {}"),
    **dict.fromkeys(("sed", "awk", "tee", "dd", "touch", "mkdir"), "change files with {}"),
    "gh": "use the GitHub CLI",
}  # fmt: skip


# Verbs worth naming when an unlisted program is given them (R5: delete, push,
# publish, send).
ARG_VERBS = {
    "publish": "publish with {}",
    "release": "publish with {}",
    "push": "push with {}",
    "send": "send a message with {}",
    "delete": "delete things with {}",
    "remove": "delete things with {}",
    "rm": "delete things with {}",
    "uninstall": "delete things with {}",
}


def _spoken(prog: str, args: list[_Word] | None = None) -> str:
    name = prog.rsplit("/", 1)[-1]
    if not re.fullmatch(r"[\w.+-]{1,32}", name):
        return UNCHECKED
    for w in args or ():
        if not w.dynamic and w.text in ARG_VERBS:
            return ARG_VERBS[w.text].format(name)
    template = SPOKEN.get(name)
    return f"run {name}" if template is None else template.format(name)


# --- command classification --------------------------------------------------


def classify_command(command: str, depth: int = 0) -> Verdict:
    try:
        return _classify_command(command, depth)
    except Exception:  # noqa: BLE001 — fail closed
        return _ask(UNCHECKED)


def _classify_command(command: str, depth: int) -> Verdict:
    if len(command) > MAX_COMMAND_CHARS:
        return _ask("run a very long command")
    if not command.strip():
        return _ask(UNCHECKED)
    if any((ord(c) < 32 and c not in "\t\n") or ord(c) == 127 for c in command):
        return _ask(UNCHECKED)
    try:
        commands = split_commands(command, depth)
        if not commands:
            return _ask(UNCHECKED)
        for words in commands:
            reason = _check_simple(words, depth)
            if reason is not None:
                return _ask(reason)
    except _Unsupported as e:
        return _ask(e.reason)
    return _allow("read-only command")


def _check_simple(words: list[_Word], depth: int) -> str | None:
    """None if this simple command is read-only, else the spoken reason."""
    args: list[_Word] = []
    for w in words:
        if w.redirect:
            if w.quoted or not SIMPLE_REDIRECT.fullmatch(w.text):
                return "write a file with a redirect" if ">" in w.text else "read through a redirect"
            continue
        args.append(w)
    if not args:
        return None  # only harmless redirects
    prog, rest = args[0], args[1:]
    if prog.quoted or prog.dynamic or "/" in prog.text or "=" in prog.text:
        return UNCHECKED if prog.dynamic else _spoken(prog.text, rest)
    name = prog.text
    if name in SHELLS or name == "eval":
        return _check_shell_payload(name, rest, depth)
    checker = SAFE_PROGRAMS.get(name)
    if checker is None:
        return _spoken(name, rest)
    return checker(rest)


def _check_shell_payload(name: str, rest: list[_Word], depth: int) -> str | None:
    if name == "eval":
        if not rest or any(w.dynamic for w in rest):
            return "run commands through eval"
        payload = " ".join(w.text for w in rest)
    else:
        if len(rest) != 2 or rest[0].text != "-c" or rest[1].dynamic:
            return f"run commands through {name}"
        payload = rest[1].text
    verdict = classify_command(payload, depth + 1)
    return None if verdict.allowed else verdict.reason
