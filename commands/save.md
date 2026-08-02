---
description: End-of-session checkpoint — finalize the wiki cluster, reconcile hub state, regenerate rollups, lint, then commit + push.
---

<!--
TEMPLATE NOTE — localize before use:
- <vault> = your knowledge-base vault root (scaffolded from wiki-template/ in
  this repo). Replace with your real path or keep ~ shorthand.
- `python` below means the interpreter of your vault's virtualenv — invoke it
  however your platform does (activated venv, `python3`, a venv-relative
  binary). The manifest and binding-lint scripts ship in
  wiki-template/scripts/; the state-reconcile and pending helpers are
  adopter-local — if you haven't built them, do those steps by hand or skip
  them (every tooling step here is best-effort, never a commit blocker).
- Set your own commit co-author trailer (or drop it).
-->

Checkpoint the current session: finalize the wiki cluster, write a handoff, and
commit + push the work. Run this when wrapping up or before a context reset.

This command bundles the end-of-session routine that is otherwise done by hand.
Follow these steps in order. If $ARGUMENTS is given, treat it as a one-line
note about what this session was about and fold it into the summary/commit
message.

## Step 1 — Finalize the wiki cluster
- Identify the session cluster opened this session under
  `<vault>/nodes/<YYYY-MM-DD>-<slug>/` (or a project's `wiki/nodes/...`). If
  one was opened, finalize its `_summary.md`: flip `status: draft` →
  `status: stable`, replace the "in progress" TL;DR with a real ≤80-word
  summary, and make sure durable artifacts (decisions, patterns) are filed
  with `part_of` edges back to `_summary.md`.
- Scan the wiki manifest for the topic hubs this session's work touched. Add
  `related_to` edges in the `_summary.md` frontmatter (primary 0.8, secondary
  0.5, tertiary 0.3) and mirror them as wikilinks under `## Connections`.
  Announce in chat: *"Filed cluster under: [[topics/X]], [[topics/Y]]."* If no
  hub fits, announce: *"No hub fits — left unbound for lint."*
- Append a one-line entry to the relevant `log.md`.
- If NO cluster was opened this session but the work was substantial (edited
  durable files, made decisions), create one now and finalize it the same way.
- If the session was trivial chat with no durable work, skip this step and say
  so.

## Step 2 — Reconcile hub current-state
- For each topic hub the cluster bound to in Step 1: read the hub's
  `## Current state` block. If it has none yet, note "needs bootstrap" and
  skip it (do not auto-create on a normal save).
- Compare the finalized cluster `_summary` against that block and decide, per
  subsection: `append` genuinely new info, `replace` a subsection this session
  contradicts, `set_state` if the headline moved, else `noop`.
- Preview the change (dry-run of your state-reconcile helper, e.g.
  `python <vault>/scripts/state/reconcile_state.py --hub <hub> --ops <temp.json> --dry-run`),
  show the diff as a "here's where we are" status update, and apply only on
  the user's confirmation. **Gate every change behind a yes** — do not apply
  silently.
- If the reconcile tooling errors or doesn't exist, skip it, leave the state
  untouched, and note "state reconcile skipped" in the Step 6 report. State
  maintenance must never block the commit/push.

## Step 3 — Reconcile hub pending work
- For each hub bound in Step 1, read its `### Pending / future directions`
  subsection. Decide three things **semantically** (judgment, not a script),
  then show ALL of it as one gated diff per hub before applying:
  1. **Add** — open threads, decisions, or improvements this session surfaced
     that aren't already tracked → `- [ ] (P?, <today>) one-liner`.
  2. **Retire** — items finished or now obsolete. Remove from the hub and
     append a `resolved`/`dropped` line to `<vault>/log.md`. **Completed items
     never linger in the hub** — no checkbox graveyard; history lives in
     `log.md`.
  3. **Prioritize** — assign/adjust `P1|P2|P3` by real importance: P1 =
     bug / data-loss / blocking / security; P2 = important feature or gap;
     P3 = chore. A forgotten bug outranks a forgotten push.
- Refresh the pending rollup (e.g.
  `python <vault>/scripts/hygiene/gen_pending.py`) so the vault-level
  `PENDING.md` reflects the new state; it commits with the session in Step 5.
- Failure isolation: if anything errors, skip pending maintenance, note
  "pending reconcile skipped" in Step 6, and never block the commit/push.

## Step 4 — Regenerate the manifest and lint bindings
- Regenerate the manifest so next session's protocol scan sees this session's
  hubs and clusters: `python <vault>/scripts/gen_manifest.py`
  (ships in `wiki-template/scripts/`).
- Run the binding lint: `python <vault>/scripts/lint_binding.py`
  (also in `wiki-template/scripts/`) — it catches finalized clusters left
  unbound to any hub and malformed edges. Fix flags now if cheap; otherwise
  report them. A red lint is surfaced, not a hard commit blocker — but green
  is the goal every save.

## Step 5 — Commit and push
- The finalized `_summary.md` IS the handoff in this system — make sure its
  "Next steps" section is concrete enough that a fresh session could resume
  cold. Re-state any decision made this session in one line each so drift is
  catchable later.
- Auto-detect the git repo(s) with uncommitted changes: the current working
  directory's enclosing repo, and the vault repo if the cluster lives there.
  There may be more than one — handle each.
- For each repo with changes: `git add` the relevant files, show a short diff
  summary, and commit with a clear message (incorporate $ARGUMENTS if given).
  End every commit message with your co-author trailer if you use one.
- Reference-fleet convention: commits AND pushes happen without asking —
  checkpointing is the whole point of this command. Only stop for a yes on
  genuinely higher-risk pushes: force-push, history rewrites, or pushing a
  repo that isn't yours. (Adopters who prefer a confirmation gate: add one
  here.)
- If a repo is on its default branch (main/master) and your conventions
  require branching, branch first.

## Step 6 — Report
- Print a tight summary: cluster slug + hubs bound, lint/manifest status,
  repos committed and pushed (with branch + short hash per repo). Nothing
  else.
