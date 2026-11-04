# Higher-fidelity animation: when and with what

Default to CSS transitions and plain SVG/Canvas updates. Reach for a library
only when it does substantial work the page can't do cleanly by hand, and only
when the motion explains something (see `motion.md`).

| Need | Use | Notes |
| --- | --- | --- |
| Sequenced, step-through explanations (A happens, then B, then C), scrubbable timelines, morphing shapes, animated text splits | **GSAP** | Free for all uses, including the formerly paid plugins (SplitText, MorphSVG, …), since 2025-04-30 under the standard "no charge" license (check gsap.com/standard-license). The `gsap-trial` package is deprecated; use `gsap`. |
| Data-driven diagrams: bars, axes, graphs that transition between states | **D3** | Binds data to SVG with built-in transitions. Good for charts that change as the reader moves a slider. |
| Many moving points (embedding clouds, particles, thousands of cells) | **Canvas 2D** | No library needed; redraw per frame with `requestAnimationFrame`. |
| 3D or very large point sets | WebGL (e.g. Three.js) | Only if 2D truly can't show it. It costs load time and complexity. |

Rules:
- Pin exact versions and load from a CDN the host allows (for Claude artifacts:
  cdnjs, jsDelivr, unpkg).
- Animation shows cause → effect: the control moves, then the change plays out.
  Never play an animation the reader didn't trigger, except a short first-load
  demo that loops at most once.
- Every timeline has a reduced-motion path: jump to the end state.
- Measure: a page should still be interactive within about 1 second on a laptop.
- Verify a library's API against its current docs before writing code; don't
  rely on memory.
