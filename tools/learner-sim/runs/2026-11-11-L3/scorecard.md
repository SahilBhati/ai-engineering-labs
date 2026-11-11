# Learner-sim scorecard: Lesson 3, Training and inference economics (2026-11-11-L3, vs 2026-11-10-L3-r2)

3 runs, 41 questions. Gate: **PASS**.

| Metric | Value | Target | Before |
| --- | --- | --- | --- |
| Grounded (≥ 2 of 3 runs) | 100% | 100% | 100% |
| Grounded (per run) | 100% | info | 100% |
| Agreement | 100% | 100% | 100% |
| Key disputes (open) | 0 | 0 | 0 |
| Options-only guess | 93% | info | 93% |
| Key is the longest option | 21% | ≤35% | 21% |
| Lesson flags (confirmed) | 3 | → 0 | 3 |
| Coverage (concepts) | 100% | 100% | 100% |
| Coverage (teaching steps) | 100% | info | 100% |
| Screenshots viewed (worst run) | 100% | 100% | 100% |
| Visual-only cites | 5% | info | 2% |

## Weak distractors (right from options alone)

- L3-examples-02: 3/3 runs
- L3-loss-03: 3/3 runs
- L3-mask-01: 3/3 runs
- L3-mask-02: 3/3 runs
- L3-mask-03: 3/3 runs
- L3-scale-03: 3/3 runs
- L3-base-01: 3/3 runs
- L3-base-02: 3/3 runs
- L3-sft-01: 3/3 runs
- L3-sft-02: 3/3 runs
- L3-sft-03: 3/3 runs
- L3-preference-01: 3/3 runs
- L3-preference-02: 3/3 runs
- L3-latency-02: 3/3 runs
- L3-batching-01: 3/3 runs
- L3-batching-03: 3/3 runs
- L3-outcost-01: 3/3 runs
- L3-outcost-02: 3/3 runs
- L3-costpm-03: 3/3 runs
- L3-pcache-01: 3/3 runs
- L3-pcache-02: 3/3 runs
- L3-pcache-03: 3/3 runs
- L3-pcache-04: 3/3 runs
- L3-quant-02: 3/3 runs
- L3-quant-03: 3/3 runs
- L3-mask-04: 3/3 runs

## Confirmed lesson flags

- S09 unclear-visual (3/3): The chosen/rejected bar chart is empty at step 0, and its caption is cut off ('nothing trained yet. Pre'). A newcomer can't tell what the axis shows before pressing Train.
- S11 unclear-visual (2/3): On the left chart the y-axis '0' label collides with the orange dot at batch 1, and the right-hand 27 ms ceiling is unexplained.
- S16 term-before-taught (2/3): 'tensor parallelism' is named only in passing and 'tensor cores' appears earlier in S15, neither explained.
