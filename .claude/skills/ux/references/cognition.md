# Cognition: least effort that isn't the idea itself

Readers skim; many now arrive through an agent's summary and only open the page
to check or go deep. Every bit of effort they spend should go to the concept,
not to the page. Technical depth stays; friction goes.

## Three kinds of load (Sweller's cognitive load theory)

| Load | Source | What to do |
| --- | --- | --- |
| Intrinsic | The concept's real difficulty | **Manage**: sequence, pre-train, segment. Never dumb it down. |
| Extraneous | Design: clutter, hunting, decoding, split attention | **Eliminate** |
| Germane | The work of building understanding | **Invite**: interaction, prediction, questions |

## Principles (Mayer's multimedia principles + UX practice)

Reduce extraneous load:
1. **Coherence**: cut words, pictures and motion that aren't needed for this
   idea. Tangents go behind "Go deeper".
2. **Signaling**: make the organization and the key change visible: one color
   for "the thing that changed", the key result in bold, consistent section labels.
3. **Spatial contiguity**: words go next to what they describe. Label inside
   the visual, the control next to its effect, never "see the figure above".
4. **Temporal contiguity**: the effect appears the moment the control moves
   (within 100 ms), not after a "submit".
5. **No redundancy**: don't say the same thing in a caption, a label and a
   paragraph.

Manage intrinsic load:
6. **Segmenting**: one idea per screen, at the reader's pace.
7. **Pre-training**: introduce the names and basic meaning of key terms before
   the mechanism that uses them (e.g. dot product and softmax before attention).
8. **Concrete before abstract**: a worked example in small numbers first, then
   the general rule.
9. **Chunking**: at most 3 controls per visual and 7 items per group.

Invite germane effort:
10. **Explorable explanations** (Bret Victor): let the reader change inputs and
    test the claim themselves; text becomes an environment to think in.
11. **Retrieval**: questions at the end, without answers attached.

Help people orient:
12. **Answer first**: each page and step opens with its one-sentence takeaway.
    Someone who reads only that sentence still learns something true.
13. **Recognition over recall**: always show where you are, what's done and
    what's next; recap the previous step in one line when building on it.
14. **Consistency** (Jakob's law): the same control behaves the same way
    everywhere, and a color means the same thing in every lesson.
15. **Plain language**: short sentences (about 20 words or fewer on average),
    active voice; every technical term defined at first use.
16. **Progressive disclosure, but never for navigation**: depth can hide, the
    way around can't.

## Cognitive benchmark (score each step or section pass/fail)

C1–C10 check form. C11–C12 check comprehension: a lesson can pass every form
check and still be unreadable if steps don't connect or skip a building block.

| # | Check | Pass when |
| --- | --- | --- |
| C1 | Takeaway first | The first sentence states the idea, not a setup |
| C2 | Words | The main text is ≤ 40 words; extra goes behind "Go deeper" |
| C3 | New terms | ≤ 2 new terms, each defined where it first appears |
| C4 | Controls | ≤ 3 controls in the visual |
| C5 | Contiguity | Labels sit on the visual; no legend or "above/below" references needed |
| C6 | Immediate effect | Changing a control updates the result within 100 ms |
| C7 | Signal | The changing or important value is visually marked |
| C8 | Orientation | Position, progress and the next action are visible without scrolling |
| C9 | Concrete first | Mechanisms start with a small worked example |
| C10 | Consistency | Colors and controls mean the same as on other pages |
| C11 | Through-line | The step moves the lesson's one running example or question forward |
| C12 | Prerequisites | Every mechanism or term the step relies on was taught in an earlier step (or a recap) |

Report the pass rate (e.g. "C: 41/50 = 82%"), list the failing checks per step,
and set a target (≥ 90%). Re-run after each change: this is how the site improves
over time instead of by taste.
