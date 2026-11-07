# hark

**Voice control for the Mac: a local wake word, local speech in and out, a
rules router for fixed commands, and Claude Code as the brain for
everything else. Dangerous actions need a spoken yes.**

Status: **scaffold.** The interfaces and a fake end-to-end turn exist, with
no real audio and no real brain yet.

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
| `hark/stubs/` | A fake adapter for every port. |
| `tests/` | A fake turn as text, through every stub, asserting the event sequence and stage timings. |

Real adapters (audio, router, brain, gate, event log) each live in their
own package behind a port and are tested on their own, without audio or the
other parts. Hark's own logic never imports the audio framework; only the
audio adapters do.

## Run the tests

```bash
uv run pytest
```

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). No runtime
dependencies yet.
