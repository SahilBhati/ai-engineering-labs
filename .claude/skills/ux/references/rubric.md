# UX rubric

Score each criterion 1–5 from a desktop screenshot (and the page source if
needed). **Pass:** average ≥ 4 and no criterion below 3.

| # | Criterion | 5 looks like | 1 looks like |
| --- | --- | --- | --- |
| 1 | Hierarchy | Squint test: headline and primary action lead immediately | Everything competes at the same weight |
| 2 | Spacing rhythm | Values from one scale; groups clearly separated; generous section gaps | Arbitrary gaps; cramped; groups blur together |
| 3 | Alignment | Few strong vertical lines; consistent edges | Ragged edges; elements float |
| 4 | Typography | One scale, comfortable line length, clear heading/body contrast | Many sizes; long lines; weak heading contrast |
| 5 | Color | One accent used with restraint; tinted neutrals; contrast passes in both themes | Many competing colors, or flat gray; contrast failures |
| 6 | Affordance | Interactive things look interactive; one obvious primary action | Can't tell what's clickable; several "primary" buttons |
| 7 | Wayfinding | You know where you are, what's here and what's next (nav state, breadcrumbs, progress) | No current-location cue; dead ends |
| 8 | Density | Right amount per screen for the task; nothing important below a fold for no reason | Wall of content, or a sparse page with no substance |
| 9 | Motion | Purposeful, fast, respects reduced motion (or none needed) | Decorative, slow, or janky motion |
| 10 | Identity | A detail only this subject would have; doesn't read as a template | Generic template look |

## Report format

```
Scores: 1 H 4 · 2 S 3 · 3 A 4 · … · avg 3.7 (fail: Spacing 3, Identity 2)
Top fixes (highest impact first):
1. <what> → <concrete change, e.g. "section padding 48px → 96px; tokens --space-12">
2. …
3. …
```

Fixes name the element, the change, and the token or value. "Make it pop" is
not a fix.
