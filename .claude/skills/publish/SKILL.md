---
name: publish
description: Turns approved items from docs/publish-queue.md into site pages and documentation in this repository, one item per run, on a branch. Use when the user says "publish", "work on the site", "update docs", or has spare tokens to use. Pushes only what a recorded standing permission covers; never reads private repositories or folders outside this repository.
---

# publish: approved items → site and docs, on a local branch

## Boundaries (enforced, not optional)

- Work **only inside this repository**. Never read or write any path outside it,
  including private vaults or notes. Everything you need is in the queue item and
  in `publish-staging/`.
- **Push and merge what a standing permission in `docs/publish-queue.md` covers**
  (currently: every change, pushed right away, once the checks below pass). A
  failing QE gate or personal-data check always stops the push.
- One queue item per run. If the queue has no item with status `approved`, stop
  and say so.
- No personal data: names of people other than the author, employers' internal
  details, private paths. If a staged source contains any, stop and report it.

## Steps

1. Read `docs/publish-queue.md`. Take the first item with status `approved`.
2. Create a branch from `main`: `publish/<YYYY-MM-DD>-<short-slug>`.
3. Do the item:
   - **site/**: plain static HTML/CSS/JS, no build step and no dependencies,
     so it can be served by any static host. Lesson pages: copy from
     `publish-staging/`, remove the private answer store (no `claude.use`), keep
     the interactive steps, and add the site header and footer.
   - **docs/** or a tool README: write for a stranger. Pitch first, then install,
     quick start, how it works.
4. Check: run the behavior suite `node tools/site-qe/qe.mjs site` (it needs
   Node 22+ and Chrome). **Any failing check blocks the push**: report it and
   stop. Then grep the diff for personal paths (`/Users/`) and stop if any appear.
5. Commit on the branch with a clear message. Set the item's status to
   `ready for review (branch publish/…)` in the queue file in the same commit.
6. If every changed file is covered by a standing permission: merge the branch
   into `main` (fast-forward), push, and set the item's status to `published`.
   Then redeploy the live site, which GitHub Pages serves from the `gh-pages`
   branch: `git subtree split --prefix site -b gh-pages && git push origin gh-pages`,
   and confirm the changed pages return HTTP 200 at
   https://sahilbhati.github.io/ai-engineering-labs/.
   Otherwise report the branch, the files changed, what to look at, and the
   command to publish once approved: `git push -u origin <branch>`.

Done when one item is done on a branch and the queue shows its status: `published`
if a standing permission covered every file and it was pushed, otherwise
`ready for review` with nothing pushed.
