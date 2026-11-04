# Motion

Motion must do a job: **feedback** (this responded), **orientation** (where
this came from and went), or **continuity** (the same object changed state).
Motion that only decorates gets cut.

## Timing

| Use | Duration |
| --- | --- |
| Hover, press, toggle feedback | 100–150 ms |
| Small component change (menu, tooltip, chip) | 150–250 ms |
| Panel, drawer, card expanding | 250–350 ms |
| Large or full-screen transition | 400–600 ms |

Bigger and farther-moving elements take longer. Nothing in everyday UI needs
more than ~600 ms.

## Easing

- Entering: ease-out (fast start, gentle stop). Exiting: ease-in.
- A good default for state changes is Material 3's standard curve,
  `cubic-bezier(0.2, 0, 0, 1)`; verify against m3.material.io before treating it
  as canon.
- Never linear, except for progress bars and continuous spinners.

## Performance and access

- Animate only `transform` and `opacity` (they're cheap for the browser).
  Avoid animating width, height, top or left.
- Respect `prefers-reduced-motion: reduce`: remove movement, keep instant state
  changes or plain fades.
- Content is visible at rest. Never hide text at `opacity: 0` waiting for a
  scroll observer.

## Patterns that earn their place

- A button responds within 100 ms (color or a slight scale to 0.98).
- Numbers in a calculator ease to their new value (~200 ms) so the change reads.
- An interactive diagram animates from cause to effect when a control moves.
- Page sections don't fly in on scroll.
