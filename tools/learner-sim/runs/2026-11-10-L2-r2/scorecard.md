# Learner-sim scorecard: Lesson 2, The block, sampling, the KV cache (2026-11-10-L2-r2, vs 2026-11-10-L2)

3 runs, 34 questions. Gate: **FAIL**.

| Metric | Value | Target | Before |
| --- | --- | --- | --- |
| Grounded | 95% | 100% | 98% |
| Agreement | 100% | 100% | 100% |
| Key disputes (open) | 0 | 0 | 1 |
| Options-only guess | 95% | info | 95% |
| Key is the longest option | 28% | ≤35% | 94% |
| Lesson flags (confirmed) | 0 | → 0 | 3 |
| Coverage (concepts) | 100% | 100% | 100% |
| Coverage (teaching steps) | 93% | info | 93% |
| Screenshots viewed (worst run) | 100% | 100% | 100% |
| Visual-only cites | 1% | info | 3% |

## Not grounded in every run

- L2-mlp-05: grounded 1/3, correct 3/3
- L2-logits-01: grounded 2/3, correct 3/3
- L2-sampling-03: grounded 2/3, correct 3/3
- L2-prefill-03: grounded 2/3, correct 3/3

## Weak distractors (right from options alone)

- L2-mlp-01: 2/3 runs
- L2-mlp-04: 3/3 runs
- L2-mlp-05: 3/3 runs
- L2-residual-01: 3/3 runs
- L2-residual-02: 3/3 runs
- L2-residual-03: 3/3 runs
- L2-stack-03: 3/3 runs
- L2-logits-01: 3/3 runs
- L2-temperature-01: 3/3 runs
- L2-temperature-03: 3/3 runs
- L2-sampling-03: 3/3 runs
- L2-loop-01: 2/3 runs
- L2-kvcache-01: 3/3 runs
- L2-kvcache-02: 3/3 runs
- L2-kvcache-03: 3/3 runs
- L2-prefill-01: 3/3 runs
- L2-prefill-02: 3/3 runs
- L2-prefill-03: 3/3 runs
- L2-kvsize-04: 2/3 runs
- L2-context-02: 3/3 runs

## Uncovered

- step S03

## Since last run

- lost grounding: L2-logits-01
- lost grounding: L2-sampling-03
- lost grounding: L2-prefill-03
