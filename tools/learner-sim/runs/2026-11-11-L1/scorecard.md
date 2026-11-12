# Learner-sim scorecard: Lesson 1, Tokens, embeddings, attention (2026-11-11-L1, vs 2026-11-10-L1-r3)

3 runs, 36 questions. Gate: **PASS**.

| Metric | Value | Target | Before |
| --- | --- | --- | --- |
| Grounded (≥ 2 of 3 runs) | 100% | 100% | 100% |
| Grounded (per run) | 99% | info | 99% |
| Agreement | 100% | 100% | 100% |
| Key disputes (open) | 0 | 0 | 0 |
| Options-only guess | 100% | info | 97% |
| Key is the longest option | 27% | ≤35% | 27% |
| Lesson flags (confirmed) | 4 | → 0 | 3 |
| Coverage (concepts) | 100% | 100% | 100% |
| Coverage (teaching steps) | 90% | info | 90% |
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
- L1-weights-01: 2/3 runs
- L1-weights-02: 3/3 runs
- L1-basics-03: 3/3 runs
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

- S01 term-before-taught (3/3): 'MLP', 'layer', 'scores' used in the diagram before they are explained; Lesson 2 covers them.
- S08 unclear-visual (2/3): Scatter plot has no axis labels; at 0% the dots show random placement and the bank dot is clipped ('deposi' cut off); no color legend.
- S15 term-before-taught (2/3): 'backpropagation' and 'output row' / second table appear with only a one-line definition; step size is used in the nudge formula without being taught.
- S17 term-before-taught (2/3): 'residual connection' is mentioned without explanation (deferred to next lesson); bank's key is shown as [1,1] though keys are 'picked by hand', so the matrices W_K and W_V are not shown.
