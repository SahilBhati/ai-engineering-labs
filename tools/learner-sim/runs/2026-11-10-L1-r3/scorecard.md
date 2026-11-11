# Learner-sim scorecard: Lesson 1, Tokens, embeddings, attention (2026-11-10-L1-r3, vs 2026-11-10-L1-r2)

3 runs, 36 questions. Gate: **PASS**.

| Metric | Value | Target | Before |
| --- | --- | --- | --- |
| Grounded (≥ 2 of 3 runs) | 100% | 100% | 97% |
| Grounded (per run) | 99% | info | 98% |
| Agreement | 100% | 100% | 100% |
| Key disputes (open) | 0 | 0 | 0 |
| Options-only guess | 97% | info | 97% |
| Key is the longest option | 27% | ≤35% | 27% |
| Lesson flags (confirmed) | 3 | → 0 | 1 |
| Coverage (concepts) | 100% | 100% | 100% |
| Coverage (teaching steps) | 90% | info | 85% |
| Screenshots viewed (worst run) | 100% | 100% | 100% |
| Visual-only cites | 0% | info | 0% |

## Not grounded in every run

- L1-tokens-07: grounded 2/3, correct 3/3

## Weak distractors (right from options alone)

- L1-machine-01: 3/3 runs
- L1-machine-02: 3/3 runs
- L1-tokens-01: 3/3 runs
- L1-tokens-02: 3/3 runs
- L1-tokens-03: 3/3 runs
- L1-tokens-04: 2/3 runs
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
- L1-basics-03: 3/3 runs
- L1-basics-04: 3/3 runs
- L1-gradient-01: 3/3 runs
- L1-gradient-02: 3/3 runs
- L1-attention-01: 3/3 runs
- L1-attention-02: 3/3 runs
- L1-attention-03: 3/3 runs
- L1-attention-04: 3/3 runs
- L1-heads-02: 3/3 runs
- L1-cost-03: 3/3 runs

## Uncovered

- step S06
- step S16

## Confirmed lesson flags

- S01 term-before-taught (2/3): 'scores', 'MLP', 'layers' used in overview without explanation; deferred to Lesson 2 (acceptable but newcomer-opaque)
- S15 term-before-taught (3/3): 'output row'/'second learned table' used before taught (deferred to Lesson 2); also quiz Q28 asks about 'output table' as weight which is only lightly covered
- S17 unclear-visual (2/3): Screenshot shows the score/softmax table empty and blend greyed before pressing Next phase; initial state teaches nothing and 'new bank = [0.00, 0.00]' is shown, contradicting the S14 blend [0.26, 2.38] the text promised

## Since last run

- now grounded: L1-attention-02
- lost grounding: L1-tokens-07
