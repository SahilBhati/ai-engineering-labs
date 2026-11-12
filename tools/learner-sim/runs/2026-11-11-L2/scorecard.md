# Learner-sim scorecard: Lesson 2, The block, sampling, the KV cache (2026-11-11-L2, vs 2026-11-10-L2-r3)

3 runs, 34 questions. Gate: **PASS**.

| Metric | Value | Target | Before |
| --- | --- | --- | --- |
| Grounded (≥ 2 of 3 runs) | 100% | 100% | 100% |
| Grounded (per run) | 100% | info | 98% |
| Agreement | 100% | 100% | 100% |
| Key disputes (open) | 0 | 0 | 0 |
| Options-only guess | 100% | info | 95% |
| Key is the longest option | 28% | ≤35% | 28% |
| Lesson flags (confirmed) | 2 | → 0 | 1 |
| Coverage (concepts) | 100% | 100% | 100% |
| Coverage (teaching steps) | 93% | info | 93% |
| Screenshots viewed (worst run) | 100% | 100% | 100% |
| Visual-only cites | 2% | info | 4% |

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
- L2-loop-01: 3/3 runs
- L2-kvcache-01: 3/3 runs
- L2-kvcache-02: 3/3 runs
- L2-kvcache-03: 3/3 runs
- L2-prefill-01: 3/3 runs
- L2-prefill-02: 3/3 runs
- L2-prefill-03: 3/3 runs
- L2-kvsize-04: 3/3 runs
- L2-context-01: 2/3 runs
- L2-context-02: 3/3 runs

## Uncovered

- step S03

## Confirmed lesson flags

- S07 term-before-taught (3/3): 'gated MLP', 'key and value weights' sharing heads and 'width' used before taught (GQA only in 2.3)
- S08 term-before-taught (3/3): softmax relies on 'Basics, step 12' pointer; and '[0.26, 2.38] (recap)' refers to a recap value never shown in the recap steps

## Since last run

- now grounded: L2-kvcache-02
- now grounded: L2-kvsize-02
