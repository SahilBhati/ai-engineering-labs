# Learner-sim scorecard: Lesson 4, Give the model knowledge (2026-11-12-L4, vs 2026-11-11-L4-r3)

3 runs, 37 questions. Gate: **PASS**.

| Metric | Value | Target | Before |
| --- | --- | --- | --- |
| Grounded (≥ 2 of 3 runs) | 100% | 100% | 100% |
| Grounded (per run) | 99% | info | 100% |
| Agreement | 100% | 100% | 100% |
| Key disputes (open) | 0 | 0 | 1 |
| Options-only guess | 94% | info | 90% |
| Key is the longest option | 24% | ≤35% | 24% |
| Lesson flags (confirmed) | 3 | → 0 | 1 |
| Coverage (concepts) | 100% | 100% | 100% |
| Coverage (teaching steps) | 100% | info | 100% |
| Screenshots viewed (worst run) | 100% | 100% | 100% |
| Visual-only cites | 0% | info | 2% |

## Not grounded in every run

- L4-split-02: grounded 2/3, correct 3/3

## Weak distractors (right from options alone)

- L4-closed-01: 3/3 runs
- L4-closed-02: 3/3 runs
- L4-rag-01: 3/3 runs
- L4-rag-02: 3/3 runs
- L4-rag-03: 3/3 runs
- L4-chunk-01: 3/3 runs
- L4-chunk-02: 3/3 runs
- L4-chunk-03: 3/3 runs
- L4-choose-01: 3/3 runs
- L4-choose-02: 3/3 runs
- L4-choose-03: 3/3 runs
- L4-embed-01: 3/3 runs
- L4-embed-02: 3/3 runs
- L4-embed-03: 3/3 runs
- L4-hybrid-01: 3/3 runs
- L4-hybrid-02: 3/3 runs
- L4-ann-02: 3/3 runs
- L4-ann-03: 3/3 runs
- L4-floor-01: 3/3 runs
- L4-floor-02: 3/3 runs
- L4-floor-03: 3/3 runs
- L4-golden-03: 3/3 runs
- L4-golden-04: 3/3 runs
- L4-split-02: 3/3 runs
- L4-judge-01: 3/3 runs
- L4-judge-02: 3/3 runs
- L4-judge-03: 3/3 runs
- L4-gate-01: 3/3 runs
- L4-gate-03: 3/3 runs

## Confirmed lesson flags

- S01 term-before-taught (2/3): recap uses 'dot product' and 'dimensions' with only a one-line reminder; fine for engineers but 'token embedding' relies on Lesson 1 memory
- S08 term-before-taught (2/3): 'Lucene-BM25' in the evidence is used before BM25 is explained (explained only in S09 go-deeper)
- S09 term-before-taught (2/3): Go deeper says 'step 12 shows which' referencing steps by number while chapters label steps 1-12 differently from S-ids; also hybrid keyword ranks (#1, #3) are shown only in text, not in the keyword view I could see

## Since last run

- lost grounding: L4-split-02
