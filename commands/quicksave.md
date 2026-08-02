---
description: Quick mid-session checkpoint — flush working memory into the wiki (cluster summary + hub state/pending + rollup) without git. Auto-fires at ~30% context remaining.
---

<!--
TEMPLATE NOTE — localize before use:
- <vault> = your knowledge-base vault root (scaffolded from wiki-template/).
- `python` = your vault virtualenv's interpreter, invoked however your
  platform does it. The state/pending helper scripts referenced below are
  adopter-local; if you haven't built them, do those steps by hand or skip
  them — every tooling step is best-effort.
- The ~30% auto-trigger is a hook on the reference fleet (a context-level
  watcher that fires /quicksave); wire your own or run it manually.
-->

Quick mid-session checkpoint: flush working memory into the wiki nodes
(session cluster summary + touched project hubs' state/pending + the PENDING
rollup) WITHOUT the end-of-session ceremony. No git, no push. Run this
whenever you want decisions captured durably but aren't wrapping up yet.

`/quicksave` is the lightweight subset of `/save`: it does the vault-node
updates and nothing else. Use `/save` when you actually want to commit + push
and finalize the session. If $ARGUMENTS is given, treat it as a one-line note
about what to capture and fold it into the cluster `_summary` TL;DR.

**Assume a context reset may follow.** Quicksave is the pre-reset checkpoint
(the auto-trigger at ~30% remaining context fires it precisely so the session
can be cleared afterward). Write the cluster `_summary` as a RESUME-GRADE
HANDOFF: what's done (with commit hashes), what remains (exact next steps,
file paths, entry points), and open caveats — a fresh session must be able to
continue from the `_summary` + referenced plan/spec alone, with zero memory of
this conversation.

Apply all node changes behind **one batch gate**: gather the full set of
proposed edits, show ONE compact diff (cluster-summary delta + per-hub
state/pending deltas), and apply the whole batch only on a single "yes." Do
not gate per-hub like `/save`.

## Step 1 — Update the session cluster `_summary.md`
- Identify the cluster opened this session under
  `<vault>/nodes/<YYYY-MM-DD>-<slug>/` (or a project's `wiki/nodes/...`).
  Refresh its TL;DR to reflect current state and fold in $ARGUMENTS if given.
  Make sure durable artifacts created since the last checkpoint are filed with
  `part_of` edges back to `_summary.md`.
- **Do NOT force `status: draft → stable`** — quicksave is a mid-session
  flush, so the cluster usually stays `draft`. Flip to `stable` only if the
  work is clearly finished.
- If NO cluster was opened but the session produced durable work (decisions,
  edits to durable files), open one now with a draft `_summary.md` and fill it.
- If the session is trivial chat with no durable work, skip this step and say
  so.

## Step 2 — Reconcile touched project hubs (state + pending)
For each topic hub this session's work touched:
- **Current state:** compare the cluster `_summary` against the hub's
  `## Current state` block and decide per subsection: `append` new info,
  `replace` a contradicted subsection, `set_state` if the headline moved, else
  `noop`. If the hub has no `## Current state` block yet, note "needs
  bootstrap" and skip it — quicksave does not auto-create state blocks.
- **Pending:** in the hub's `### Pending / future directions`, **add** open
  threads/decisions/improvements this session surfaced
  (`- [ ] (P?, <today>) one-liner`), **retire** items finished or obsolete
  (remove from hub; log a `resolved`/`dropped` line to `<vault>/log.md` — no
  checkbox graveyard), and **prioritize** P1/P2/P3 by real importance (P1
  bug/data-loss/blocking/security, P2 important gap, P3 chore).
- Fold these into the single batch diff from the gate above. Preview state ops
  with your reconcile helper's dry-run (e.g.
  `python <vault>/scripts/state/reconcile_state.py --hub <hub> --ops <temp.json> --dry-run`);
  on the yes, re-run with `--apply`.

## Step 3 — Refresh the PENDING rollup
- Run `python <vault>/scripts/hygiene/gen_pending.py` (or your equivalent) so
  the vault-level `PENDING.md` reflects the new pending state.
- If a NEW hub was created this session, run your hub-classification lint and
  fix any flag. Otherwise skip the lint.

## Step 4 — Append to log and report
- Append a one-line entry to the relevant `log.md` noting the quicksave.
- Print a tight summary: cluster slug, hubs reconciled (state/pending deltas
  applied), and `PENDING.md` refreshed. Remind the user that nothing was
  committed — `/save` still does the git commit + push.

## Failure isolation
Every wiki-tooling step is best-effort: if a helper script errors or doesn't
exist, skip that piece, note "<step> skipped" in the Step 4 report, and keep
going. A quicksave must never crash — at worst it captures less than intended
and says what it skipped.
