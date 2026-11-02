# triage — managed by AGF

Drain the inbox and propose a filing batch. Part of the AGF skill
factory: this skill is managed by AGF, it is not the tool itself.

Factory rules that apply: propose, don't write. Agents write only to
100-Inbox and 800-Agent-Records. Changes to core notes arrive as a git
commit batch that the user explicitly approves. Approval is never
inferred from agent-editable text.

1. Take each item in 100-Inbox in turn: enrich it (title, frontmatter,
   source, confidence), resolve entities, and drop exact duplicates.
2. Wire wikilinks to existing notes; check that every new note links
   to at least one existing note.
3. Propose a batch: the files, their destination folders, and a
   one-line reason each. Present the batch for approval. Never write
   to core folders directly.

Done when: the inbox is drained or the remaining items are listed with
a reason, and every proposed change is waiting on explicit approval.
