# Color

## System

- Define colors in **OKLCH** (`oklch(L C H)`): lightness is perceptually even,
  so shades of one hue line up and contrast is predictable.
- Two layers: **primitives** (e.g. `--teal-50 … --teal-900`, 5–9 shades per hue)
  and **semantic tokens** (`--bg`, `--surface`, `--ink`, `--muted`, `--line`,
  `--accent`, `--danger`). Components use semantic tokens only. Dark mode
  redefines only the semantic layer.
- **Tinted neutrals**: give grays a slight hint of the accent hue (chroma
  0.005–0.02). Pure gray looks dead next to a colored accent.
- **One accent**, used for the primary action, links, current location and key
  numbers. Keep it under ~10% of the screen. Status colors (success, warning,
  danger) are separate from the accent.
- Design in grayscale first; add color last.

## Contrast

- WCAG 2: body text ≥ 4.5:1, large text (≥ 24 px, or ≥ 19 px bold) and UI
  components ≥ 3:1. This is the compliance baseline.
- APCA (candidate for WCAG 3, not yet a standard): body text |Lc| ≥ 75, ≥ 90
  preferred. Use as a second check.
- To fix contrast in OKLCH, change **L** only; chroma barely matters.
- Muted text still needs 4.5:1. "Subtle" that fails contrast is unreadable.

## Dark mode

- Never invert the light palette. Build dark surfaces as their own steps:
  background darkest, surfaces slightly lighter, borders a little lighter again.
- Lower the accent's chroma as you raise its lightness for dark backgrounds,
  or it glows.
- Check contrast in both themes separately: a pair that passes in light mode
  can fail in dark.

## Depth

- Elevation with surface lightness steps and subtle borders, not heavy shadows.
- One border color for the whole UI; a stronger one only for focus and
  selection.
