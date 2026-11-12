# Learner-sim scorecard: Lesson 3, Training and inference economics (2026-11-10-L3)

3 runs, 41 questions. Gate: **FAIL**.

| Metric | Value | Target |
| --- | --- | --- |
| Grounded | 98% | 100% |
| Agreement | 100% | 100% |
| Key disputes (open) | 0 | 0 |
| Options-only guess | 100% | info |
| Key is the longest option | 100% | ≤35% |
| Lesson flags (confirmed) | 4 | → 0 |
| Coverage (concepts) | 100% | 100% |
| Coverage (teaching steps) | 100% | info |
| Screenshots viewed (worst run) | 100% | 100% |
| Visual-only cites | 1% | info |

## Not grounded in every run

- L3-outcost-02: grounded 2/3, correct 3/3
- L3-costpm-02: grounded 2/3, correct 3/3

## Weak distractors (right from options alone)

- L3-examples-02: 3/3 runs
- L3-loss-03: 3/3 runs
- L3-loss-04: 3/3 runs
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
- L3-capacity-01: 3/3 runs
- L3-mask-04: 3/3 runs

## Confirmed lesson flags

- S04 term-before-taught (2/3): 'cross-entropy', 'logits' and 'backpropagation' used with only a passing gloss; backprop named but only explained in a parenthetical
- S06 term-before-taught (3/3): 'tensor/optimizer state', 'activations', 'stragglers' and 'checkpoint' used without explanation
- S09 unclear-visual (2/3): Bars for chosen/rejected both show 0.00 at step 0 with no scale; the RLHF/DPO toggle diagram is just labels
- S16 term-before-taught (2/3): 'tensor parallelism' named only in passing in the explanation
