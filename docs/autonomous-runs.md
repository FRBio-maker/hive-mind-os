<!--
TEMPLATE NOTE — this doc is the protocol, not a runnable skill. The reference
fleet implements it as a private "lonewolf" skill; that implementation is NOT
shipped here (it is dense with machine-specific dispatch mechanics). The
shipped skills/consult, skills/council, skills/delegate-external,
skills/browser-ops and the commands/ templates are its dependencies — an
adopter who has localized those can implement this protocol as a skill of
their own.
-->

# Autonomous runs — the lonewolf protocol

How the hive-mind runs a project **unsupervised and overnight-safe**: the
human states a goal, goes to sleep, and reads one report over coffee. The
protocol's job is to make that safe — every rule below exists because the
human cannot answer questions until morning.

## The shape of a run

The session that receives the goal **becomes the CEO agent**. It does not
write code; it specs, partitions, dispatches, verifies, and reports. Below it:
orchestrator subagents (one per work package), and below those, hive workers
dispatched per `routing.toml`.

```
CEO (this session — small context footprint: assignment doc + summaries only)
 ├─ Orchestrator subagent  — work package P1 (bounded context budget)
 │    └─ workers per routing.toml (external CLIs, cheap-tier API, subagents)
 ├─ Orchestrator subagent  — work package P2
 └─ …
```

## The CEO safety rails (hard charter — never violated)

1. **All work happens in an isolated worktree on a feature branch.** The live
   system stays untouched.
2. **Never merge to main / the integration branch.** The merge is the human's
   morning gate. Rollback = don't merge.
3. Commit and push the feature branch freely; **no force-push, no history
   rewrite, no deleting outside the worktree**.
4. **No metered paid APIs.** Subscription CLIs in the roster and free-tier
   endpoints are fine; anything billed per token while the human sleeps is
   not.
5. **Nothing that changes durable non-repo state** — no firmware, hardware,
   scheduler/system config, no user data outside the worktree.
6. **Never block on the human** — see defer-and-log below.
7. A task is **done** only when its runnable check passes. No green check, no
   done.
8. **Restore the fleet's mode state** (`mode.state` back to `present`) at the
   end of the run — on the normal path AND on the crash path. An autonomous
   run that dies must not leave the control plane believing the human is
   still away.

## Phase 0 — Spec and design gate

1. **Load context** per the wiki protocol (manifest scan, hub TL;DRs, the
   project's newest spec/plan if it's a registered project).
2. **Spec the goal**: assumptions stated, approach designed, "complete"
   defined.
3. **Mandatory `/consult` on the design** (see `docs/decision-protocol.md`).
   The cross-vendor review substitutes for the human's judgment on the plan
   itself — it is never skipped.
4. **Write the assignment doc** — the run's single source of truth. Plan,
   live state, and morning report are the same file, updated as the run
   progresses. It holds: the morning-report block, the charter echo
   (branch/worktree/time cap), the work-package table (scope, size,
   worker routing, runnable done-check, status, checkpoint notes), the
   per-package briefs, a timestamped decision log, and the deferred-decisions
   list.

**Package sizing:** partition by *scope* (files touched, expected tool calls,
whether tests run) — never by token guesses; models misestimate token burn
2–3×. Size every package to fit comfortably inside a bounded orchestrator
context budget (**~150K tokens on the reference fleet**); when in doubt,
split. Packages must be as independent as possible so a blocked one never
stalls the run.

## Phase 1 — Execution loop

Spawn **one orchestrator subagent per work package**; run independent
packages concurrently. The CEO keeps a small footprint — it reads the
assignment doc and orchestrator summaries, never worker transcripts.

Every orchestrator brief contains: the package scope + done-check + relevant
spec sections **inlined** (subagents don't inherit context), the delegation
context (`routing.toml` location, `skills/delegate-external/` mechanics, and
the wiki/project context that makes delegates effective — never stripped to
save tokens), the charter verbatim, and the **hand-off rule**: if the package
turns out bigger than scoped, STOP before context degrades, write a
checkpoint (done / next / exact resume point) into the assignment doc, and
return — a fresh orchestrator resumes from the checkpoint.

Workers are dispatched per `routing.toml`: terminal-agentic grinds,
long-context edits, live web research, decision-free bulk work each go to the
roster entry that owns that class; judgment work stays on same-family
subagents. Defer to the TOML over any hardcoded list.

**Question tiers** (escalate only when the tier below fails):

1. Worker question → orchestrator answers from the spec.
2. Spec doesn't cover it → CEO decides; if genuinely ambiguous, `/council`
   (internal, free, fast). Log the decision.
3. Real design fork with lasting consequences → full `/consult`. Log the
   verdict.
4. Consult splits with no clear verdict, or the answer requires a charter
   violation → **defer-and-log**: write it under "Deferred decisions" with a
   recommendation, mark dependent tasks blocked, continue with everything
   else. The run never pages a sleeping phone and never stalls waiting for a
   human.

**Per-package verification gate** (before a package is marked done):

1. **Run the done-check** and paste its actual output into the doc. For UI
   work the check is *behavioral*: a browser click-through
   (`skills/browser-ops/`) of every interactive element touched, verifying
   the region that should change actually shows the new state — "no error
   thrown" is not a pass. (Proven the hard way: a dashboard run once shipped
   every action button broken past four visual review passes; only clicking
   caught it.)
2. **Code review on the package's diff** — the internal multi-agent bug hunt.
   Free and fast, so it runs first: cheap bugs die here instead of burning
   external roster quota.
3. **`/consult` on the package's diff** — logic bugs caught here localize to
   one package instead of surfacing in the whole-branch sweep.
4. **Debt review on the touched scope** (an over-engineering / maintainability
   audit) — fix cheap findings now, log the rest.
5. Commit with a message naming the package ID.

External-CLI throughput is the constraint: **serialize the per-package
consults** (one package's gate at a time) to stay under roster rate limits;
the package *builds* can still run concurrently.

**Failure policy:** worker fails → retry once with an augmented brief
(include the failure output) → escalate to a different worker per
`routing.toml` → mark the package `blocked` with evidence and move on. Never
silent, never an infinite retry loop.

**Heartbeat:** after every package status change, update the morning-report
block and commit it. Fire-and-forget progress pings only — never wait on a
reply.

## Phase 2 — Wrap-up

1. **Code review on the whole branch** (free, internal) — so the final
   consult reviews an already-debugged tree.
2. **Final `/consult` on the finished branch** — the integration-level pass:
   cross-package interactions, contract mismatches, whole-system logic.
3. **Full debt review** on the branch's touched scope.
4. **Re-run every package's done-check** on the final tree — regressions from
   later packages are the classic miss.
5. **Full-app browser click-through sweep** (only if the project has a UI;
   otherwise say so in the report). Execution model: **manifest once, replay
   deterministically** — one agent crawls the app and emits a test manifest
   (selector + expected-state assertion per element, covering *every*
   user-selectable element in the whole app, including state-gated UI:
   modals, tabs, wizards, post-login views), then a browser test runner
   replays it headless with a few workers. Destructive actions
   (delete/reset/logout/mutating submits) are deny-listed in the manifest and
   run last, serialized, against restorable state. Verdicts are DOM-first
   (assertions + accessibility-tree diffs); screenshots are evidence, not the
   oracle; never ship an unreleased app's full UI to a free-tier vision API
   that may train on it. Record a per-element pass/fail table.
6. **Finish the morning report:** what shipped (commit hashes), what's
   blocked and why, deferred decisions with recommendations, and the exact
   preview + merge commands for the human's go/no-go.
7. **Checkpoint: run `/save`** (see `commands/save.md`) — finalize the wiki
   cluster, commit, push, hand off. And per charter rail 8, restore
   `mode.state`.

## Stop conditions

Stop — and still complete the Phase 2 wrap-up; the report matters most when
the run stopped early — when any of: all packages `done` or `blocked`; the
wall-clock cap passed at invocation is reached; or two consecutive
orchestrator spawns fail on the same package after the full failure policy
(systemic problem — stop burning the night on it).

## Failure modes the protocol absorbs

- **Context exhaustion** → package sizing + the hand-off rule turn it into a
  checkpointed resume, not a degraded agent.
- **CEO crash / compaction** → the assignment doc is durable state; a fresh
  session pointed at it resumes idempotently (skip `done`, respawn
  `in-progress` from checkpoints).
- **Worker flakiness** → the failure policy + verified dispatch mechanics in
  `routing.toml`.
- **Plausible-but-broken output** → behavioral done-checks, not visual
  review.
- **Runaway burn** → stop conditions + each package's bounded worker-routing
  plan + charter rail 4.

## See also

- `docs/decision-protocol.md` — the council/consult gates this run leans on
- `docs/playbooks/CEO-PLAYBOOK.md` — the CEO role this session assumes
- `skills/consult/`, `skills/council/`, `skills/delegate-external/`,
  `skills/browser-ops/` — the shipped dependencies
- `commands/save.md` — the end-of-run checkpoint
- `config-templates/hivemind/routing.toml` — the worker roster
