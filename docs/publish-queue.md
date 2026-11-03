# Publish queue

Items the `/publish` skill may turn into site pages or docs. Only items with
status `approved` are worked on, one per run. The owner approves items. Sources
that are not already in this repository are staged in `publish-staging/`, which
git ignores.

Statuses: `proposed` → `approved` → `ready for review (branch …)` → `published`.

**Standing permission (owner, 2026-11-02):** changes under `site/` (and this queue
file) may be committed, pushed and merged to `main` without asking, because the
site isn't announced yet. Everything else still needs the owner's yes: other
folders, enabling hosting, announcing the site. The personal-data check stays
mandatory.

| # | Item | Source | Status |
| --- | --- | --- | --- |
| 1 | Site skeleton under `site/`; see **Site brief** below | none | approved (owner, 2026-11-02) |
| 2 | Lesson 1: tokens, embeddings, basics, attention (interactive, no answer store) | `publish-staging/lesson-1.1-1.3.html` | proposed |
| 3 | AGF docs: README refresh for the profile mechanism, plus `docs/agf.md` explaining the factory model | `tools/agf/` | proposed |

## Site brief (approved by the owner with item 1, 2026-11-02)

Reference for *structure only*: aihero.dev, a learning site built around free
tutorials, courses and events, where public pages also exist as Markdown for
agents. Build our own identity: never reuse its name, copy, logo or visual style.

- **Positioning line:** LLM internals and AI infrastructure, explained for software
  engineers by building things.
- **Content types:** Lessons (interactive, grouped into courses, e.g. "LLM
  Foundations for engineers"), Write-ups (labs and projects with measured
  results), Tools (AGF), About (short portfolio).
- **Home:** positioning line, latest lessons, featured project, tools, about.
- **Agent-readable:** every content page also as `.md`, plus a `/llms.txt` index.
- **Build:** static HTML/CSS/JS, no build step, no dependencies, phone-first,
  light and dark themes, served from `site/` by any static host.
- **Hosting:** not decided. Enabling GitHub Pages or any host is public and needs
  the owner's yes.
