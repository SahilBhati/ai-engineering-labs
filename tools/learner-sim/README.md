# learner-sim: measure a lesson and its quiz with a simulated learner

A capable model already knows the material, so a raw quiz score says nothing
about a lesson. learner-sim scores **grounding** instead: a simulated learner
(`.claude/agents/learner-sim.md`, a strong engineer with no ML background)
reads the lesson step by step, text and screenshots, answers the lesson's
quiz bank **only from what the lesson taught**, and cites the step behind
every answer. Quotes are checked against the step text mechanically.

Three independent runs per lesson (fresh context each) give agreement and
majority votes. It's a publish gate per lesson, not a continuous monitor.

## Run

```bash
node tools/learner-sim/run.mjs all 3                 # prepare + 3 runs + score, Lesson 3
node tools/learner-sim/run.mjs prepare 3             # capture steps, build packets -> runs/<date>-L3
node tools/learner-sim/run.mjs sim 2026-11-10-L3     # 3 parallel `claude -p --agent learner-sim` runs
node tools/learner-sim/run.mjs score 2026-11-10-L3   # scorecard.json + scorecard.md, diff vs previous run
node --test tools/learner-sim/score.test.mjs         # unit tests for the pure scoring core
```

Needs Node 22+, Chrome, and the `claude` CLI (for `sim`). Runs use Sonnet.

## Metrics

| Metric | Definition | Target |
| --- | --- | --- |
| Grounded | share of questions grounded in ≥ 2 of 3 runs; a run grounds a question when it is correct **and** cites a teaching step with a verified quote (or a described visual) | 100% |
| Grounded (per run) | the same, counted over every run's answers; a slip in one run shows here | info only |
| Agreement | same answer in every run; disagreement marks the question ambiguous | 100% |
| Key disputes | the actor says the question is flawed by the lesson's own content; a human reviews each | 0 open |
| Options-only guess | choice question answered right from its options alone in ≥ 2 of 3 runs | info only |
| Key is the longest option | single-choice key strictly longer than every distractor (chance ≈ 25%) | ≤ 35% |
| Lesson flags | per step: term before taught, unclear visual, inconsistent highlight, C1–C12 fails; confirmed when ≥ 2 of 3 runs raise it | trending to 0 |
| Coverage | bank concepts with ≥ 1 question grounded in ≥ 2 of 3 runs (teaching-step coverage reported too) | 100% |

The gate passes when Grounded, Agreement, Key disputes, Key-longest,
Coverage and Screenshots viewed all meet target. Flags are tracked as a trend.

Options-only is reported but not gated: the actor knows the subject, so it
can spot the true option without the question; that says little about a
beginner. Key-is-longest is the model-free check for a cue a person could game.

**The human learner is ground truth.** When real quiz misses disagree with
the actor's verdict, fix the actor's instructions or this scoring, not the
learner.

## Files

```
lib/score.mjs     pure scoring: grade (via the quiz engine), cite checks, aggregate, diff, Markdown
lib/packet.mjs    pure: bank -> per-run packet (opaque ids Q01…, seeded shuffle, no answers)
run.mjs           capture (headless Chrome), sim (claude CLI), score (files)
disputes.json     disputes a human reviewed and closed: {"L3": {"L3-cost-02": "key kept: …"}}
runs/<date>-L<n>[-rK]/
  steps.json      every step's id, chapter, title, text (screenshots are regenerated, not committed)
  keys/map-K.json Q01 -> bank id and option shuffle (the actor never reads this)
  run-K/packet/   what the actor sees
  run-K/options-only.json, run-K/answers.json   what the actor wrote
  scorecard.json, scorecard.md
```

## Limits

- Screenshots show each visual in its default state; the actor can't drag a
  slider. A fact only visible after interaction shows up as "not grounded".
- A visual cite is accepted on the actor's description; the share of
  visual-only cites is reported so it can be watched.
