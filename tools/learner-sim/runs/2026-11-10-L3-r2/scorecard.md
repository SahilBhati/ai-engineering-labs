# Learner-sim scorecard: Lesson 3, Training and inference economics (2026-11-10-L3-r2, vs 2026-11-10-L3)

3 runs, 41 questions. Gate: **PASS**.

| Metric | Value | Target | Before |
| --- | --- | --- | --- |
| Grounded | 100% | 100% | 98% |
| Agreement | 100% | 100% | 100% |
| Key disputes (open) | 0 | 0 | 0 |
| Options-only guess | 93% | info | 100% |
| Key is the longest option | 21% | ≤35% | 100% |
| Lesson flags (confirmed) | 3 | → 0 | 4 |
| Coverage (concepts) | 100% | 100% | 100% |
| Coverage (teaching steps) | 100% | info | 100% |
| Screenshots viewed (worst run) | 100% | 100% | 100% |
| Visual-only cites | 2% | info | 1% |

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
- L3-latency-02: 2/3 runs
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

- S09 term-before-taught (2/3): σ (sigmoid) in 'σ(gap)' is used with no explanation of what it computes; 'reinforcement learning' and 'reward model' are named but not explained.
- S09 unclear-visual (3/3): Before training the bars show only 0.00 and the axis is unlabeled, so a newcomer can't tell what the bar scale or direction means until they press Train.
- S11 term-before-taught (2/3): 'memory-bound' and 'math-bound' are used with no earlier explanation. The L2 recap in S01 doesn't cover them.

## Since last run

- now grounded: L3-outcost-02
- now grounded: L3-costpm-02
