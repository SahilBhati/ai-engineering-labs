# Learner-sim scorecard: Lesson 2, The block, sampling, the KV cache (2026-11-10-L2)

3 runs, 34 questions. Gate: **FAIL**.

| Metric | Value | Target |
| --- | --- | --- |
| Grounded | 98% | 100% |
| Agreement | 100% | 100% |
| Key disputes (open) | 1 | 0 |
| Options-only guess | 95% | info |
| Key is the longest option | 94% | ≤35% |
| Lesson flags (confirmed) | 3 | → 0 |
| Coverage (concepts) | 100% | 100% |
| Coverage (teaching steps) | 93% | info |
| Screenshots viewed (worst run) | 100% | 100% |
| Visual-only cites | 3% | info |

## Not grounded in every run

- L2-mlp-05: grounded 1/3, correct 3/3

## Key disputes (human review)

- L2-kvsize-02: Lesson's 328 KB/token is 327,680 bytes ×8192 = 2.68 GB; rounding to 2.7 is the only ambiguity.

## Weak distractors (right from options alone)

- L2-mlp-01: 3/3 runs
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
- L2-context-02: 3/3 runs

## Uncovered

- step S03

## Confirmed lesson flags

- S05 term-before-taught (2/3): 'frozen at inference' uses 'inference' without definition
- S07 term-before-taught (3/3): 'final scoring step' and 'logit lens' invoked before logits are taught in next chapter (forward reference)
- S14 term-before-taught (3/3): uses compute-bound / memory-bandwidth-bound, H100, FasterTransformer before explaining them (only glossed by analogy)
