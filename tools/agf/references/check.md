# check — managed by AGF

Run a no-model vault lint. Part of the AGF skill factory: this skill
is managed by AGF, it is not the tool itself.

Factory rules that apply: report only. Fixes arrive as a proposed
batch, never as silent edits.

Run the lint with grep:

1. Broken wikilinks: every `[[Link]]` target must resolve to an
   existing note file.
2. Orphans: every note must have at least one inbound or outbound
   wikilink.
3. Missing frontmatter: every note must carry type, status, created,
   and updated; knowledge notes must also carry source and confidence.
4. Stale notes: notes untouched for more than 90 days, listed for
   review, not auto-archived.

Write the report to 800-Agent-Records.

Done when: the report exists, lists every finding by category, and no
core file was modified.
