# Typography

- At most two families: one sans for UI and text (or a display face for
  headings only), one mono for code, numbers and labels.
- A modular scale (ratio ~1.25): 12, 14, 16, 18, 20, 24, 30, 36, 48, 60. Pick
  from it; never invent sizes.
- Body 16–18 px, line height 1.5–1.7. Headings line height 1.05–1.2, slight
  negative letter-spacing (−0.01 to −0.03 em) at large sizes.
- Prose at 60–75 characters per line (`max-width: 65ch`).
- Small uppercase labels: mono or medium weight, letter-spacing 0.08–0.12 em,
  muted color. Use them to name sections, not as decoration.
- `font-variant-numeric: tabular-nums` wherever digits line up.
- `text-wrap: balance` on headings; avoid single-word last lines.
