---
name: agf
description: Manages a self-learning markdown vault as a skill factory: sets up a vault, triages an inbox into linked notes, lints vault health, and turns repeated mistakes into rules — always proposing changes as git batches for human approval, never writing core notes silently. Use when the user wants to set up a second brain or knowledge vault, organize notes, triage an inbox, lint or restructure a vault, manage agent skills, or run a self-learning vault system. Do not use for one-off note edits, for writing to a vault without approval, or for a vault the user does not want an agent to maintain.
license: MIT
compatibility: Requires git and a markdown vault; Obsidian optional; works with any Agent Skills-compatible agent.
metadata:
  version: 0.1.0
---

# AGF — a skill factory

AGF is a tool in itself. It is not a single skill. AGF manages skills —
and the vault and learning loop those skills operate on. An agent using
AGF loads this factory model first, then runs the managed skills in
`references/` as needed.

## Factory model

- **One trustworthy shared picture.** Every claim cites its source and
  when that source was last refreshed. Conflicts between sources are
  marked, stale data shows as stale, and an unknown state shows as
  unknown. Never present a guess as a fact.
- **One ranked Needs-you inbox.** Questions, approvals, disagreements,
  and learnings land in one place, blocking first, then decisions,
  then FYI. Agents never ask through scattered chat, and never block
  on the human: every question carries a recommended answer and a
  working assumption, and work continues on that assumption until the
  answer arrives.
- **Propose, don't write.** Agents write only to the inbox and to
  agent records. Changes to core notes arrive as a batch — a set of
  files plus a summary, committed as one git commit — that applies
  only after the user's explicit yes. Approval is never inferred from
  agent-editable text.
- **Learning loop.** Misses against rules are logged. A miss repeated
  3 times becomes a rule candidate the user accepts or rejects.
  Accepted rules enter the structure note or agent protocol as a
  proposed batch, never as a silent edit.
- **Local and plain.** Markdown plus git, no new dependencies, no
  cloud. A private vault stays private. Removing the skill removes
  the skill, never the vault.

## Router — which routine runs when

| User wants | Run | Output |
| --- | --- | --- |
| Start a session on a vault | `references/start.md` | Session brief in agent records |
| Clear an inbox into the vault | `references/triage.md` | Proposed filing batch, awaiting approval |
| Check vault health | `references/check.md` | Lint report in agent records, report only |
| Record a miss or draft a rule | `references/learn.md` | Miss log, or a rule candidate on third repeat |

Load a routine file only when its row applies. Do not load all four
up front.

## Setup — resolve VAULT_ROOT once

On first use with a vault, ask the user for the vault's path and
record it in the session brief (in the vault's agent-records folder)
so later sessions reuse it. If the agent platform supports persistent
skill config, store it there instead.

All routines reference vault paths through `$VAULT_ROOT` — for
example `$VAULT_ROOT/100-Inbox`, `$VAULT_ROOT/000-Meta`,
`$VAULT_ROOT/800-Agent-Records`. Never assume a vault path, and never
write an absolute personal path into the skill.

If the vault is empty, copy `vault-template/` (shipped with this
package) into it first: it provides the folder skeleton, the
structure note, and the Map-of-Content template. The template's
numbering (000–900) is the layout the routines expect; if the user's
vault uses different folders, map its folders to these roles in the
session brief before running any routine.
