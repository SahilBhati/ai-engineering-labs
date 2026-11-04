---
name: ux
description: Designs and improves web UI with a repeatable method (brief, references, grayscale structure, design tokens, build, screenshot, score, fix the top issues) instead of taste. Scores both visual quality and cognitive load (how little effort a reader spends on anything but the idea). Covers hierarchy, layout, color (OKLCH, contrast, dark mode), typography, motion, animation libraries, and cognitive-load principles for explaining technical topics. Use when building or restyling a page, site, artifact or app UI, or when the user says the UI looks average, cluttered or off. Not for copywriting or backend work.
license: MIT
metadata:
  version: 0.2.0
---

# ux: design by method, not by taste

Good UI comes from a few rules applied consistently and checked by looking.
Work through these stages in order. Load a reference file only when its stage
needs it.

Two lenses, both required. **Visual**: does it look clear and considered?
**Cognitive**: does the reader spend effort only on the idea itself? Read
`references/cognition.md` first: it decides structure and wording, which matter
more than color.

## 1. Brief (5 lines, written down)

The page's single job, who it's for, the one primary action, what must be
visible without scrolling, and a mood in three words (e.g. "calm, precise,
technical"). If the user named a reference site, note which **patterns** to
borrow (structure, navigation, density); never its name, copy, logo or palette.

## 2. References

Study 1–3 references at desktop width before designing. Capture every top-level
section the user points at, not only the home page, and get links from the real
page rather than guessing URLs. How to capture: `references/screenshots.md`.
Write down 5–8 concrete patterns per reference (e.g. "sticky left nav grouped
by section", "numbered tiles sharing borders").

## 3. Structure in grayscale

Lay out with no color: hierarchy must come from size, weight, spacing and
position alone. Rules: `references/hierarchy-layout.md`. Then the squint test:
blur your eyes; the primary heading and primary action should still stand out.

## 4. Tokens

Define everything once in `:root`, then use only tokens:
- Color: `references/color.md`
- Type: `references/type.md`
- Spacing: a 4px-based scale (4, 8, 12, 16, 24, 32, 48, 64, 96)
- Motion: `references/motion.md`; higher-fidelity animation: `references/animation-libraries.md`

## 5. Build, then look

Build the page, take **one** desktop screenshot (1440–1600 px wide), and look.

## 6. Score and fix

Score the screenshot with `references/rubric.md` (visual, 10 criteria) and
the page's steps or sections with the cognitive benchmark in
`references/cognition.md` (C1–C10). Fix the three highest-impact issues across
both, look once more, score again. Stop when visual averages ≥ 4 with no
criterion below 3 and the cognitive pass rate is ≥ 90%, or after two rounds;
then report what remains instead of looping. Keep each round's scores, so
improvement is tracked over time.

For an independent critique, use the `ux-reviewer` agent: it screenshots and
scores but never edits, so the builder doesn't grade their own work.

Done when the brief is met, visual ≥ 4 average with no criterion below 3 and
cognitive ≥ 90% (or the remaining gaps are reported), and nothing meant to be read
waits on a scroll or a click to appear.
