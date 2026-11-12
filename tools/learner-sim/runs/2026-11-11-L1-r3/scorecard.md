# Learner-sim scorecard: Lesson 1, Tokens, embeddings, attention (2026-11-11-L1-r3, vs 2026-11-11-L1-r2)

3 runs, 36 questions. Gate: **FAIL**.

| Metric | Value | Target | Before |
| --- | --- | --- | --- |
| Grounded (≥ 2 of 3 runs) | 97% | 100% | 100% |
| Grounded (per run) | 97% | info | 99% |
| Agreement | 100% | 100% | 100% |
| Key disputes (open) | 0 | 0 | 1 |
| Options-only guess | 93% | info | 93% |
| Key is the longest option | 27% | ≤35% | 27% |
| Lesson flags (confirmed) | 2 | → 0 | 2 |
| Coverage (concepts) | 100% | 100% | 100% |
| Coverage (teaching steps) | 90% | info | 90% |
| Screenshots viewed (worst run) | 100% | 100% | 100% |
| Visual-only cites | 0% | info | 0% |

## Not grounded in every run

- L1-machine-02: grounded 0/3, correct 3/3

## Weak distractors (right from options alone)

- L1-machine-01: 3/3 runs
- L1-machine-02: 3/3 runs
- L1-tokens-01: 3/3 runs
- L1-tokens-02: 3/3 runs
- L1-tokens-03: 3/3 runs
- L1-tokens-05: 3/3 runs
- L1-tokens-06: 3/3 runs
- L1-tokens-07: 3/3 runs
- L1-tokens-08: 3/3 runs
- L1-embeddings-01: 3/3 runs
- L1-embeddings-03: 3/3 runs
- L1-embeddings-04: 3/3 runs
- L1-embeddings-05: 3/3 runs
- L1-embeddings-06: 3/3 runs
- L1-position-01: 3/3 runs
- L1-position-02: 3/3 runs
- L1-weights-02: 3/3 runs
- L1-basics-03: 2/3 runs
- L1-basics-04: 3/3 runs
- L1-gradient-01: 3/3 runs
- L1-gradient-02: 3/3 runs
- L1-attention-01: 3/3 runs
- L1-attention-02: 3/3 runs
- L1-attention-03: 3/3 runs
- L1-attention-04: 2/3 runs
- L1-heads-02: 3/3 runs
- L1-cost-03: 3/3 runs

## Uncovered

- step S06
- step S16

## Confirmed lesson flags

- S01 term-before-taught (2/3): Q10 (hallucination) and Q07 (four-space tokens) are not directly taught anywhere; the lesson only poses them in the S22 self-check.
- S17 term-before-taught (2/3): 'residual connection' mentioned without explanation (deferred to next lesson)
