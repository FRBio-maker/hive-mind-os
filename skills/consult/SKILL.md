---
name: consult
description: >-
  Convene a full cross-vendor decision consult — the four-voice internal council
  (Architect / Skeptic / Pragmatist / Critic) PLUS a MANDATORY external hive-mind
  review from the non-apex workers in your routing.toml roster, synthesized into
  one verdict. Use whenever the user types /consult, says "consult" on a decision,
  wants outside or second opinions, cross-model / hive-mind / multi-agent input,
  external review of a plan or architecture call, or a go/no-go stress-tested by
  other AI models — anything where the value is hearing from voices OUTSIDE the
  apex runtime, not just its own council. The mandatory external review is the
  whole point of /consult and is what makes it different from /council. If the
  user explicitly wants ONLY internal voices (fast, no external cost), use
  `council` instead.
---

<!--
TEMPLATE NOTE — localize before use:
- The external roster is NOT hardcoded here. It comes from your routing.toml
  (see config-templates/hivemind/routing.toml): every worker from a non-apex
  model family is a candidate external voice. Vendor names below (Gemini, Grok,
  GPT) are illustrative examples only.
- Dispatch mechanics (exact CLI commands, flags, timeouts) live in your
  routing.toml and the `delegate-external` skill — verify them on your machine.
-->

# Consult

Convene a decision council that spans vendors: four internal voices **plus a
mandatory external hive-mind review** from the non-apex worker roster,
synthesized into a single verdict.

**The one thing that defines this skill:** the external review is **always on**.
A council of only same-family voices is just `/council`. What makes `/consult`
worth its extra cost and latency is that the question also gets stress-tested by
*different model families* — whose blind spots don't correlate with the apex
runtime's. If you ever find yourself skipping the external step, you are running
`/council`, not `/consult`.

## When to use this vs `/council`

| Situation | Skill |
|---|---|
| Ambiguous decision, want fast structured dissent, internal voices are enough | `council` |
| Same, but you want it stress-tested by other model families / a true outside opinion | **`consult`** |
| High-stakes / irreversible / expensive call where cross-vendor agreement is worth the latency | **`consult`** |
| Prior-art or "does this already exist" matters (a web-search-capable worker can check) | **`consult`** |

Both are for **decisions under ambiguity** — not code review, not implementation
planning, not architecture *design*. If it's not a genuine fork with multiple
credible paths, just answer directly.

## Core principle: the hive advises, you decide

Routing law says *never delegate judgment* (`architecture_decision → self`).
`/consult` does not break that rule: the external agents are **advisors, not
deciders**. You (the orchestrator) form your own position first, gather the
voices, and **synthesize and own the verdict**. This is the sanctioned
`second_opinion_review` pattern — get a critique from a different family, then
decide yourself. Nobody outside the session gets to make the call; they get to
make you think harder before you make it.

---

## Workflow

### 1. Extract the real question

Reduce the decision to one explicit prompt: what are we deciding, which
constraints matter, what counts as success. If it's vague, ask **one**
clarifying question before convening — a fuzzy question wastes four internal
subagents and several external dispatches.

### 2. Write your own Architect position FIRST

Before you launch anyone, write down: your initial position, its three
strongest reasons, and the main risk in your preferred path. Do this **first**
so the final synthesis reflects your own reasoning instead of just averaging
the voices. You are both a participant and the synthesizer; this is how you
avoid anchoring on whoever spoke last.

### 3. Launch the four internal voices (parallel)

The Architect is you (already written in step 2). Launch the other three as
**fresh subagents**, each getting **only the question + compact context + its
role** — never the ongoing conversation. That context-starving is the
anti-anchoring mechanism; it's why the voices disagree usefully instead of
echoing the thread.

Role lenses:
- **Skeptic** — challenge the framing, question the premise, propose the simplest credible alternative.
- **Pragmatist** — optimize for shipping speed, real-world execution, user impact.
- **Critic** — surface downside risk, edge cases, and the concrete ways this fails.

Prompt shape for each (keep them under 300 words, no hedging):
```
You are the [ROLE] on a decision council.
Question: [decision question]
Context: [only the relevant constraints/snippets]
Respond with:
1. Position — 1-2 sentences
2. Reasoning — 3 concise bullets
3. Risk — the biggest risk in YOUR recommendation
4. Surprise — one thing the other voices may miss
```

### 4. Dispatch the external hive-mind (parallel, MANDATORY)

This is the step that makes it a consult. **Read your `routing.toml` now** for
the current roster and verified invocation flags — they drift as CLIs update,
so never hardcode them here. The mechanics live in the `delegate-external`
skill; follow it. Dispatch to **every available non-apex model family in
parallel** (external CLI calls are slow, often 40–150s each; you want them
overlapping). A typical roster spans, for example, a Gemini-family worker
(long-context expert opinion), a web-search-capable worker (prior art / "has
someone already built this"), and a third family for the
implementation-reality opinion — but the actual set is whatever `routing.toml`
lists as available.

Write **one shared consult brief** and send it to all of them. The brief asks
for an **opinion as text only — no file edits**. Use the same 4-part shape as
the internal voices (Position / Reasoning / Risk / Surprise). This is
opinion-only work, so:
- **Never** pass any worker's auto-approve / allow-edits flag. Make each
  dispatch read-only *by construction* (disallow write/edit/shell tools where
  the CLI supports it).
- Cap each dispatch with a timeout so one stalled worker can't hang the consult.

**Graceful degradation — judge each worker by its EXIT CODE, not its stderr**
(shell wrappers often echo harmless noise to stderr). If a worker fails — auth
expired, timeout, empty output, crash — note *which* one and *why*, then
proceed with whoever answered. A partial hive is fine; a silent one is not.

**The at-least-one-external rule:** a consult needs **≥1** external voice to
earn the name. If **all** externals fail (offline, auth expired everywhere), do
**not** silently hand back an internal-only result dressed as a consult. Tell
the user the hive mind was unreachable, show the internal council result, and
offer to retry the externals or fall back to `/council`. Surface the
degradation — don't hide it.

### 5. Synthesize (with bias guardrails)

You are the synthesizer, so hold yourself to these:
- Keep the raw positions visible **before** the verdict — the user should see
  the disagreement, not just your conclusion.
- Don't dismiss any voice (internal or external) without saying *why*.
- If an external voice **changed your recommendation**, say so explicitly —
  that's the whole return on paying for the hive mind.
- **Cross-vendor convergence is the strongest signal you can get.** When the
  internal council and two different outside families independently land on the
  same answer, weight that heavily — their errors are uncorrelated, so
  agreement is hard to fake.
- Always include the strongest dissent, even if you reject it. If two-plus
  voices align against your initial Architect position, treat that as real
  signal, not noise to argue past.

### 6. Present the verdict (scannable on a phone)

```markdown
## Consult: [short decision title]

**Architect (you):** [position] — [1 line why]
**Skeptic:** [position] — [1 line why]
**Pragmatist:** [position] — [1 line why]
**Critic:** [position] — [1 line why]

**<worker> (<family>):** [position] — [1 line why]   (or: unreachable — exit N, reason)
**<worker> (<family>):** [position] — [1 line why]   (repeat per roster entry)

### Verdict
- **Consensus:** [where they align]
- **Cross-vendor signal:** [did the outside families agree with the internal council, or split?]
- **Strongest dissent:** [the most important disagreement, kept legible]
- **Premise check:** [did the Skeptic challenge the question itself?]
- **Recommendation:** [your synthesized path — you own this]
```

### 7. Persist only if it changes something real

If the verdict changes real execution truth (a project direction, a locked
decision), record it in your knowledge base per your wiki protocol (see
`docs/wiki-protocol.md` in this repo for the reference scheme). If it's a
lightweight call, don't — a node per consult is noise. Persist the delta, not
the ceremony.

---

## Reliability notes

- **Latency:** external CLIs are slow. Always dispatch in parallel and cap each
  with a timeout; never block the consult on a single slow worker.
- **Trusted-directory checks:** some worker CLIs refuse to run outside a
  git/trusted directory and exit non-zero with empty output — which reads
  exactly like a silent worker. A consult is opinion-only and may run from a
  scratch location, so pass the CLI's skip-repo-check flag where one exists
  (record the verified flag in `routing.toml`).
- **Opinion-only:** no worker should touch files during a consult. If
  `git status` shows a worker edited anything, treat its output as suspect and
  discard the edits.
- **Telemetry (optional):** if your fleet keeps a delegation log, record each
  external dispatch (exec + outcome) like any other delegation so routing
  stats stay honest.

## See also

- `skills/council/` — the internal-only, no-external-cost version. Use when the hive mind is overkill.
- `skills/delegate-external/` — the exact CLI mechanics for the step-4 dispatch (read it before dispatching).
- `config-templates/hivemind/routing.toml` — the roster template; your live copy carries verified per-worker flags and model IDs (read it every dispatch; it drifts).
- `docs/decision-protocol.md` — when to fire council vs consult at all.
