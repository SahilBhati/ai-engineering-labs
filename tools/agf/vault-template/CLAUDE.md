# Vault — agent entry point

Agents that read CLAUDE.md load these at session start (L0 + L1):

@000-Meta/Profile.md
@000-Meta/Structure.md

Agents write only to 100-Inbox and 800-Agent-Records. Everything
else changes through a proposed git batch after the user's explicit yes.
