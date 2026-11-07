# hark

**Voice control for the Mac: a local wake word, local speech in and out, a
rules router for fixed commands, and Claude Code as the brain for
everything else. Dangerous actions need a spoken yes.**

Status: **scaffold + audio + safety gate.** The interfaces, a fake end-to-end
turn, real audio adapters (wake word, speech-to-text, text-to-speech), the
rules router and the safety gate with its pre-tool hook exist. No real brain
yet.

## Shape

```
wake word → listen (speech-to-text) → router ─┬─ fast: action registry ─────────┬→ speak (text-to-speech)
                                              └─ brain: "on it" → Claude Code ──┘
                                                          │
                                                 safety gate (spoken yes for
                                                 delete / push / publish / send)
```

Two paths, one pipeline:

- **Fast path**: fixed commands ("open labs") run a named local action.
  Target: done in under 1 s from end of speech.
- **Brain path**: everything else says "on it" right away, goes to one
  long-running Claude Code process, and comes back as a short spoken answer
  with any detail shown on screen.

Every stage publishes events with a turn id and a monotonic timestamp, so
each turn's latency can be broken down by stage.

## Layout (ports and adapters)

| Path | What |
| --- | --- |
| `hark/ports/` | One `Protocol` per component: `WakeWord`, `SpeechToText`, `TextToSpeech`, `Router`, `ActionRegistry` (+ `Action`), `Brain`, `SafetyGate`, `EventBus`. No implementations. |
| `hark/events.py` | Turn events: started, transcribed, routed, tool call requested/decided, confirmation asked/answered, answered, stage timed, ended. |
| `hark/turn.py` | `TurnRunner`: runs one turn through the ports and times each stage. |
| `hark/router/` | `RulesRouter`: normalises the text, vetoes destructive or negated commands, scores it against every action's phrases, and returns `FastAction` at or above 0.85, else `ToBrain`. Stdlib only, under 10 ms. |
| `hark/actions/` | `Registry` and `OpenResource`: open a URL, app or path by name with macOS `open` (R4). |
| `examples/actions.toml` | Example resources config with placeholder entries. |
| `hark/gate/` | `HarkSafetyGate` (policy decision point): `classify` (allow-list of clearly safe tool calls; everything else asks), `Confirmer` (a spoken yes must pass the F6 checks), `GateServer` (Unix socket the hook talks to), `hook_settings()` (the Claude Code settings lane C hands the brain). |
| `hark/hooks/pretool_hook.py` | The enforcement point: a standalone, stdlib-only `PreToolUse` hook. Asks Hark over the socket; allows only on a clear allow, exits 2 on anything else. |
| `examples/gate.toml` | Example gate settings (yes list, hallucination list, energy floor). |
| `bench/lane_d.py` | Latency the hook adds to an allowed tool call. |
| `hark/stubs/` | A fake adapter for every port. |
| `hark/audio/` | Real `WakeWord` (openWakeWord), `SpeechToText` (whisper.cpp server) and `TextToSpeech` (Kokoro server) adapters on one shared mic and speaker. `engine.py` is the only module in Hark that imports Pipecat. |
| `bench/lane_a.py` | Wake-word cost and accuracy, STT latency with and without the vocabulary prompt, idle CPU. |
| `tests/` | A fake turn as text, through every stub, asserting the event sequence and stage timings. |

Real adapters (audio, router, brain, gate, event log) each live in their
own package behind a port and are tested on their own, without audio or the
other parts. Hark's own logic never imports the audio framework; only the
audio adapters do.

## Configure resources

Copy `examples/actions.toml` to `~/.config/hark/actions.toml` and fill in
your own URLs, apps and paths. That file stays outside the repo because it
holds personal links. Each resource becomes one action; add a few
phrasings per resource, because the router matches close variants, not
open-ended requests.

## Safety gate

Any tool call that is not clearly read-only waits for a spoken yes; any doubt
or failure blocks. `classify` is an allow-list (`ls`, `git status`, pipes of
read-only commands, `Read`/`Glob`/`Grep`); unknown programs, interpreters,
redirects, `git push`, `Write`, MCP tools and anything it cannot parse ask.
Hark must be running for any tool call to run.

```python
from hark.gate.settings import hook_settings
settings = hook_settings("/path/to/hark/hooks/pretool_hook.py")   # pass to `claude --settings`
# and run `claude` with HARK_GATE_SOCKET set to GateServer's socket path
```

Optional settings: copy `examples/gate.toml` to `~/.config/hark/gate.toml`.

## Run the tests

```bash
uv run pytest              # no audio needed; hardware tests are skipped
uv run pytest --hardware   # also mic, speaker and the local servers
uv run pytest -m live      # drives the real `claude` CLI: fail-closed, spoken yes/no, kill-Hark
```

Requires macOS, Python 3.12+, [uv](https://docs.astral.sh/uv/) and
PortAudio (`brew install portaudio`). One test fails if any module outside
`hark/audio/` imports Pipecat.

## Try the audio

Needs a whisper.cpp server on `127.0.0.1:2022` and a Kokoro server on
`127.0.0.1:8880` (both OpenAI-compatible; settings in `hark/audio/config.py`,
or a TOML file with an `[audio]` table).

```bash
uv run python -m hark.audio --once   # say "hey jarvis", then a sentence; hear it back
```

The first run downloads the openWakeWord models. The terminal needs
microphone permission (System Settings → Privacy & Security → Microphone).
