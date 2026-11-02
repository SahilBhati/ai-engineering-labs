# AGF — a skill factory for a self-learning vault

**AGF makes your agents accountable to you: one trustworthy picture of your work, one inbox for everything they need from you, and a vault that learns — where agents propose changes and you approve them, never the other way around.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## The problem

You work with several AI agents at once. They use your time, your files,
and your knowledge — but you can't see what they are doing, what they
need from you, or what they know. Notes pile up, claims go unsourced,
and every new session starts by re-explaining everything.

## Why not just a prompt?

A paragraph in an agent's instructions can remember things. What it
can't do is give you a trustworthy *write path* across many agents:
proposed changes you can inspect, approve, and revert; claims that must
cite a source or fail; and a memory that improves itself instead of
just accumulating. That write path is what AGF is.

## The factory model

- **One trustworthy shared picture.** Every claim cites its source and
  freshness. Conflicts, stale data, and unknowns are marked, never
  dressed up as facts.
- **One ranked Needs-you inbox.** Questions, approvals, disagreements,
  and learnings land in one place — blocking first, then decisions,
  then FYI.
- **Propose, don't write.** Agents write only to the inbox and agent
  records. Core changes arrive as git batches you explicitly approve.
- **Learning loop.** Misses become rule candidates you accept or
  reject, so the system gets sharper instead of repeating mistakes.
- **Local and plain.** Markdown plus git. No new dependencies, no
  cloud, no lock-in: your vault is plain files and stays yours.

## Install

AGF v1 installs by manual copy (one-line install arrives with the
standalone public repo — AGF currently lives nested inside another
repo, so installer commands can't address it yet).

**Personal install:**

```sh
cp -r tools/agf ~/.claude/skills/agf/
```

**Project install (Codex, Cursor, OpenCode, and other
Agent Skills-compatible agents):**

```sh
cp -r tools/agf .agents/skills/agf/
```

**Prerequisites:** git, and a markdown vault (Obsidian optional).

**Verify the install:** ask your agent to list its loaded skills —
AGF should appear. Then run: *"Set up my vault with AGF"* and confirm
it asks for your vault path before doing anything else.

## Quick start

> "Set up my vault with AGF"
> → AGF asks for your vault path once, records it, and copies the
> vault template in if your vault is empty.

> "Triage my inbox"
> → AGF drains the inbox into enriched, linked notes and presents a
> filing batch for your approval. Nothing lands in core notes until
> you say yes.

> "Lint my vault"
> → AGF runs a no-model health check — broken links, orphans,
> missing frontmatter, stale notes — and writes the report to agent
> records. Report only; fixes come as a proposed batch.

## How it works

```
agf/
├── SKILL.md          # factory model + router (what agents load)
├── README.md         # this file (what humans read)
├── LICENSE           # MIT
├── references/       # managed skills, loaded on demand
│   ├── start.md      # session context + brief
│   ├── triage.md     # inbox drain + proposed batch
│   ├── check.md      # no-model vault lint
│   └── learn.md      # miss log + rule candidates
└── vault-template/   # empty vault skeleton for new users
```

| Skill | When it runs | Output |
| --- | --- | --- |
| start | Beginning of a session on a vault | Session brief in agent records |
| triage | Inbox has unprocessed material | Proposed filing batch, awaiting approval |
| check | Vault health needs checking | Lint report in agent records, report only |
| learn | A rule was missed or rework was needed | Miss log, or a rule candidate on third repeat |

The vault layout AGF creates (or adopts) uses numbered folders:
`000-Meta` (hub), `100-Inbox` (capture), `200-Core-Domains`
(knowledge), `300-Skill-Factory` (recipes), `400-Labs` (evidence),
`500-Projects`, `600-Literature` (sources), `700-Decisions`,
`800-Agent-Records`, `900-Archive`. Notes carry frontmatter
(`type`, `status`, `created`, `updated`; knowledge notes also
`source` and `confidence`) and graduate `seed → growing → evergreen`
only on human approval.

## The vault template

`vault-template/` ships an empty vault skeleton: the folder layout
above, the structure note (folder roles, required fields, load tiers,
promotion criteria, approval rule), a Map-of-Content template, an
empty profile (`000-Meta/Profile.md` — who you are and how agents
should work with you, loaded first every session), and a `CLAUDE.md`
that makes Claude Code load the profile and structure note
automatically. Your filled profile stays in your vault; AGF never
ships it.
Point AGF at an empty folder and it copies the template in, so a
stranger with no vault gets a working one on first run.

## Comparison

| | AGF | One prompt | vouch | karpathy-llm-wiki |
| --- | --- | --- | --- | --- |
| Who can write | Agents propose, human approves (git batch) | Whoever the prompt tells | Agents propose, human approves | Agent ingests, wiki compiled |
| What triggers it | Vault tasks: setup, triage, lint, learn | Any matching chat | Knowledge-base writes | Ingest, query, lint |
| What you get | A factory: managed skills + a vault that learns | A remembered preference | A review-gated claim store | A cited, linted wiki |

## Design boundaries — deliberately not built

- **No CLI.** The skill is the interface; a CLI is a later layer, not
  v1.
- **No dashboard.** Agent records and vault views carry the picture
  for now.
- **No auto-approve.** A batch without an explicit human yes never
  applies.
- **No cloud.** Everything is local files and git.
- **No embeddings.** Linking and linting are explicit and inspectable,
  not similarity scores.

## Example session

Inbox item: a saved article on retrieval-augmented generation.

1. Triage enriches it (title, frontmatter, source, confidence),
   links it to two existing notes, and proposes a batch: one new
   concept note in `200-Core-Domains`, one link added to the
   retrieval Map of Content.
2. You approve the batch.
3. It commits as one git commit. The article's claims now live in the
   vault, sourced, linked, and revertable.

## FAQ

**Does it work without Obsidian?**
Yes. The vault is plain Markdown; Obsidian is a viewer, not a
requirement.

**Does it touch my existing vault?**
Only through proposed batches. Agents write to the inbox and agent
records; core notes change only after your explicit approval, as one
revertable commit.

**What if I reject a batch?**
It doesn't apply. The proposal stays in agent records with your
reason, so the reasoning is kept even when the change isn't.

**Which agents work?**
Any agent supporting the Agent Skills standard (Claude Code, Cursor,
Codex, Gemini CLI, Copilot, VS Code, OpenCode, and others).

## Uninstall

Delete the skill folder (`~/.claude/skills/agf/` or
`.agents/skills/agf/`). Your vault is plain Markdown and stays
exactly as it is — removing the skill removes the skill, never your
notes.

## License

MIT — see `LICENSE`.

## Inspired by

- [vouch](https://github.com/vouchdev/vouch) — agents propose,
  humans approve, unsourced claims are errors.
- [karpathy-llm-wiki](https://github.com/Astro-Han/karpathy-llm-wiki)
  — ingest, cited queries, lint.
- [llm-wiki](https://github.com/mehmetgoekce/llm-wiki) — two-layer
  memory: a small always-loaded layer plus pages on demand.
- [second-brain-os](https://github.com/undefined-ui/second-brain-os)
  — a full kit: guide, starter vault, skills, commands, subagents.
