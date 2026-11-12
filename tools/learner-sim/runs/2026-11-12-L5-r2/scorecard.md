# Learner-sim scorecard: Lesson 5, Give the model hands: the agent loop and MCP (2026-11-12-L5-r2, vs 2026-11-12-L5)

3 runs, 31 questions. Gate: **FAIL**.

| Metric | Value | Target | Before |
| --- | --- | --- | --- |
| Grounded (≥ 2 of 3 runs) | 100% | 100% | 100% |
| Grounded (per run) | 99% | info | 99% |
| Agreement | 100% | 100% | 100% |
| Key disputes (open) | 1 | 0 | 0 |
| Options-only guess | 96% | info | 92% |
| Key is the longest option | 24% | ≤35% | 24% |
| Lesson flags (confirmed) | 1 | → 0 | 2 |
| Coverage (concepts) | 100% | 100% | 100% |
| Coverage (teaching steps) | 100% | info | 100% |
| Screenshots viewed (worst run) | 100% | 100% | 100% |
| Visual-only cites | 1% | info | 1% |

## Not grounded in every run

- L5-loop-05: grounded 2/3, correct 3/3

## Key disputes (human review)

- L5-mcpscope-02: Not stated directly for 12,000 tokens; computed by scaling the lesson's 2,400-token = $7.20 example (12,000 x 1,000 x $3/M = $36).

## Weak distractors (right from options alone)

- L5-notools-01: 3/3 runs
- L5-notools-02: 3/3 runs
- L5-notools-03: 3/3 runs
- L5-toolcall-01: 3/3 runs
- L5-toolcall-02: 3/3 runs
- L5-toolcall-03: 3/3 runs
- L5-toolcall-04: 3/3 runs
- L5-toolcall-05: 3/3 runs
- L5-toolcall-06: 3/3 runs
- L5-loop-01: 3/3 runs
- L5-loop-03: 3/3 runs
- L5-loop-04: 3/3 runs
- L5-loop-05: 3/3 runs
- L5-loop-06: 3/3 runs
- L5-ctxcost-03: 3/3 runs
- L5-ctxcost-05: 3/3 runs
- L5-nxm-03: 3/3 runs
- L5-mcpflow-01: 3/3 runs
- L5-mcpflow-02: 3/3 runs
- L5-mcpflow-03: 3/3 runs
- L5-mcpflow-04: 3/3 runs
- L5-mcpscope-03: 2/3 runs
- L5-mcpscope-04: 3/3 runs

## Confirmed lesson flags

- S05 term-before-taught (2/3): 'prompt injection' is named only in Go deeper, in a parenthetical, with no definition beyond the example.

## Since last run

- now grounded: L5-loop-06
- lost grounding: L5-loop-05
