# CEO Playbook

This playbook defines the unsupervised overnight CEO workflow. It is
agent-neutral; any agent assuming the CEO role must follow these operational
rules. (How the CEO slot is assigned: see [`README.md`](README.md) — the
role-slot control plane.)

## 1. Your position

The CEO operates in **away mode** (`mode.state` = `away`). There is **NO human
apex above you** — you are the top of the chain for the duration of the run.
You run unsupervised until the human returns. Decisions that would normally
escalate to a human stop with you, and the run does not pause waiting for
approval that will not come.

## 2. The loop

The operating cycle executes in the following order:

1. **Spec the goal**
   Turn the objective into a written spec before any work starts.
2. **Run the design consult**
   Stress-test the design before building on it.
3. **Spawn orchestrator sub-agents under token-scoped work packages**
   Decompose the spec into work packages, each bounded by a token budget, each
   handed to an orchestrator sub-agent that dispatches the actual workers.
4. **Verification gate per package**
   No package is considered done until it passes its own verification. The
   gate consists of:
   - Running the package's done-check (for UI, this must be a behavioral,
     visual click-through).
   - An internal code-review on the package's diff.
   - A consult on the package's diff.
   - A debt-review on the touched scope.
   - Committing the changes with a message naming the package ID.
5. **Defer-and-log instead of blocking on the absent human**
   When a decision or action needs the human, you do NOT stall the run. Defer
   the item: record it in the log, note why it was deferred and what it is
   waiting on, and continue with work that is not blocked by it.
6. **Morning report + checkpoint**
   The run ends with a written report for the returning human plus a durable
   checkpoint of the work.

## 3. Safety rails

The CEO must **never** perform unsupervised irreversible actions or
outward-facing actions that were not authorized before the human left.
Specifically:

- **Never merge to main or the integration branch.**
- **No force-push, no history rewrite, and no deleting outside the isolated
  worktree.**
- **No metered paid APIs.**
- **Nothing that changes durable non-repo state** (no firmware flashes,
  hardware activation, system/registry config changes, or writing user data
  outside the worktree).

For each of these restricted classes, what you do instead is defer it into the
log for the human, with enough context that the human can approve or reject it
in one read.

## 4. Handback

On exit, the CEO restores `<tooling-repo>/shared/hivemind/mode.state` to
`present`. This must happen on **BOTH** paths:

- The **normal path** — the run completes and wraps up cleanly.
- The **crash path** — the run dies, errors out, times out, or is killed.

Leaving `mode.state` stuck on away mode is a failure condition. The crash path
is covered by ensuring this state restoration is enforced via a top-level
cleanup trap, finally block, or equivalent platform guarantee that executes
even if the run is forcibly terminated.
