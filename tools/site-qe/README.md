# site-qe

**Behavior tests for a static site, in real headless Chrome. No dependencies: Node 22 or newer and Chrome.**

Screenshots and design reviews catch how a page looks. They miss what happens
while you use it: a sidebar that scrolls away at the end of the page, a toggle
that throws an error when clicked twice, a step that never advances. site-qe
scrolls, clicks, toggles and steps through every page, and checks what should
stay true.

## Run

```bash
node qe.mjs path/to/site                 # every .html page
node qe.mjs path/to/site -p index.html   # one page (repeatable)
node qe.mjs path/to/site --json          # machine-readable
```

Exit code 1 if anything fails, so it works as a publish gate.

Every page runs twice: once normally and once with `prefers-reduced-motion`
emulated.

## Checks

| Check | Fails when |
| --- | --- |
| `js-errors` | an uncaught error or unhandled promise rejection happens during load or interaction |
| `cls` | cumulative layout shift during load is over 0.1 (the Core Web Vitals "good" limit) |
| `h-overflow` | the page scrolls sideways |
| `pinned` | a sticky or fixed element leaves its pinned position anywhere from the top of the page to the very end (intended movement such as a header sliding away is accounted for) |
| `fonts` | a button or input uses a different font from the body text (monospace excepted) |
| `names` | a button has no accessible name |
| `toggles` | `#themeBtn`, `#navBtn` or `#tocBtn` doesn't change state, doesn't update `aria-expanded`/`aria-pressed`, or doesn't toggle back |
| `lesson-walk` | on a step-by-step page with `#next`: a step renders empty, Next is below the fold, or Next doesn't advance |
| `links` | an internal link points to a file that doesn't exist |
| `reduced-motion` | with reduced motion on, animations are still running after interaction |

## How it works

It starts headless Chrome with `--remote-debugging-port`, opens each page over
the DevTools protocol using Node's built-in `WebSocket`, injects a recorder for
errors and layout shifts before any page script runs, then evaluates a probe
in the page and reads the results back. It runs in real time, so view
transitions and animations behave as they do for a person.

## Adding a check

Found a bug by hand? Write the check that would have caught it, in the probe
in `qe.mjs`, and run it against the broken version first to confirm it fails.
