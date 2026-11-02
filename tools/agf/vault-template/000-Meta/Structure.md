# Structure — how this vault is organized

This note is the vault's map. It describes folder roles, required fields,
load tiers, and the rules for promotion and approval. It is generic: it
contains no personal data and works for any vault using this numbering.

## Folder roles

| Folder | Role | What lives here |
| --- | --- | --- |
| 000-Meta/ | Hub | This note, templates, dashboards, prompts, session memory |
| 100-Inbox/ | Working / capture | Raw drops, agent output, unprocessed material |
| 200-Core-Domains/ | Knowledge | Atomic concept notes, the durable understanding |
| 300-Skill-Factory/ | Knowledge / recipes | Reusable, tested code and prompts |
| 400-Labs/ | Evidence | Experiment logs with measured results |
| 500-Projects/ | Projects | End-to-end specs and architecture |
| 600-Literature/ | Sources | Paper summaries and course notes |
| 700-Decisions/ | Decisions | Decision records: options, choice, reason |
| 800-Agent-Records/ | Agent records | Session briefs, triage reports, miss logs, rule candidates |
| 900-Archive/ | Archive | Superseded or retired notes, kept not deleted |

Rules: folders stay at most two levels deep. Never copy the folder
structure into tags — pick one system for organization, not both.

## Required frontmatter

Every note carries:

```yaml
type: concept | lab | recipe | paper | project | decision | moc | profile
status: seed | growing | evergreen | archived
created: YYYY-MM-DD
updated: YYYY-MM-DD
```

Knowledge notes (200, 300, 600) also carry:

```yaml
source: <where the claims came from — file, URL, or citation>
confidence: high | medium | low
```

A knowledge note with no `source` is incomplete. A claim without a
source is an error, not a note.

## Load tiers

Load the smallest tier that answers the task. Rough budgets:

- L0 — identity and profile: 000-Meta/Profile.md — who the vault
  belongs to, how to work with them, hard rules. (~500 tokens,
  always loaded, before anything else)
- L1 — how to find things: this note plus the agent protocol.
  (~2,000 tokens, loaded at session start)
- L2 — what is happening now: the inbox queue, the rolling
  recent-context note, open decisions. (~2,000 tokens, as needed)
- L3 — on demand: everything else, one note or folder at a time.
  (0 tokens until opened)

Never load the whole vault. Prefer the index and Maps of Content over
full-folder reads.

## Promotion: seed → growing → evergreen

- Seed: raw or inbox-derived material, not yet rewritten.
- Growing: rewritten in the author's own words and linked to at
  least 2 other notes.
- Evergreen: titled as a claim (see below), linked to at least 3
  notes, and survived one review pass.
- Archived: superseded, retired, or no longer trusted. Moved to
  900-Archive, never deleted outright.

A weekly promotion pass proposes promotions with evidence (link
count, revisit history). The human approves. Nothing auto-promotes.

## Propose, don't write

Agents write only to 100-Inbox and 800-Agent-Records. They never edit
core notes (200, 300, 400, 500, 600) directly.

A change to core notes arrives as a batch: a set of files plus a
summary, committed as one git commit. The batch applies only after
the user's explicit yes. Approval is never inferred from
agent-editable text — a note, a comment, or a chat message the agent
could have written does not count as approval.

Reversible and cheap: decide and move on. Irreversible or expensive
(delete, publish, migrate): ask first.

## Titles state claims

A concept note's title states a claim, not a topic. Prefer "Attention
scales quadratically with sequence length" over "Attention". A title
that could hold anything will eventually hold nothing useful.

## Session memory

A rolling recent-context note lives in 000-Meta. At the end of every
session, update it: what was done, what is open, what waits on the
human. The next session starts there, not from a recap.
