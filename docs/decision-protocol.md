<!--
TEMPLATE NOTE — this doc is doctrine and ships as-is. The two skills it
describes are in skills/council/ and skills/consult/; localize those (roster,
knowledge-base paths) per their template notes, not this file.
-->

# The decision protocol — council and consult

Most of what an agent does is execution: the path is clear, so it just does
the work. This chapter covers the other case — **decisions under ambiguity**
— and the two structured tools the hive-mind uses for them.

## When a structured decision fires

Fire the protocol when a call has **multiple credible paths and no obvious
winner**:

- ambiguous tradeoffs (monorepo vs polyrepo, ship now vs polish)
- go / no-go calls with real downside either way
- architecture calls that will be expensive to reverse
- anywhere the user asks for second opinions, dissent, or outside review
- anywhere conversational anchoring is a risk — a long thread has already
  "decided" and nobody has actually stress-tested it

Do NOT fire it for code review, implementation planning, factual questions,
or obvious execution. If it isn't a genuine fork, just answer.

## Two tools, one distinction

| | `council` | `consult` |
|---|---|---|
| Voices | 4 internal (same model family) | same 4 + external workers from other model families |
| Cost / latency | free, fast (subagents only) | external CLI dispatches, ~40–150 s each |
| Use when | internal dissent is enough | you want the call stress-tested by models whose blind spots don't correlate with yours |
| Defined by | structured disagreement | the **mandatory** external review |

**`council`** (see `skills/council/`) convenes four voices — **Architect**
(correctness, long-term implications; this is the in-context agent itself),
**Skeptic** (premise challenge, simplest credible alternative), **Pragmatist**
(shipping speed, operational reality), **Critic** (edge cases, downside risk,
failure modes) — and synthesizes their disagreement into one verdict. It runs
entirely inside the apex runtime: fast, no external cost.

**`consult`** (see `skills/consult/`) is the same council **plus a mandatory
cross-vendor external review** — and that addition is the hive-mind's defining
move. The question is dispatched, in parallel, to every available worker from
a *different model family* in `routing.toml` (see `docs/multi-runtime.md` for
the fleet model). The reasoning: one model family shares one set of blind
spots; a second family's errors are largely uncorrelated with the first's, so
**cross-vendor convergence is the strongest signal available** — when the
internal council and two outside families independently land on the same
answer, that agreement is hard to fake. Conversely, an outside voice that
breaks the internal consensus is exactly the input the thread could never have
generated for itself. A consult that skips the external step is just a
council; the skill treats ≥1 external voice as the minimum for the name, and
requires the degraded case (all externals unreachable) to be *surfaced*, never
silently papered over.

## The anti-anchoring mechanism

The reason the voices are subagents at all — instead of the agent role-playing
four opinions in-thread — is **isolation**. Each non-Architect voice is
launched as a fresh subagent that receives **only the decision question, a
compact context pack, and its role — never the ongoing conversation**. A voice
that has read the whole thread inherits the thread's momentum and echoes it;
a context-starved voice has nothing to anchor on but the question itself.
That's what makes the disagreement real rather than performed.

The second half of the mechanism is ordering: **the Architect position is
written down FIRST**, before any other voice is launched or read — the
position, its three strongest reasons, and the main risk in it. The
synthesizer is also a participant; committing to a position up front is what
prevents the final verdict from being a weighted average of whoever spoke
last. External consult voices get the same treatment: one shared brief,
opinion-as-text-only, no file edits, read-only by construction.

## Synthesis and the verdict

The orchestrator synthesizes under explicit bias guardrails:

- raw positions stay visible **before** the verdict — the user sees the
  disagreement, not just the conclusion
- no voice is dismissed without a stated reason
- if a voice **changed the recommendation**, that is said explicitly — it's
  the whole return on convening
- two-plus voices aligned against the initial Architect position is treated
  as real signal, not noise to argue past
- the strongest dissent is always included, even when rejected

The report is compact and phone-scannable: each voice's position with a
one-line why, then a verdict block — **Consensus / Strongest dissent /
Premise check** (did the Skeptic challenge the question itself?) **/
Recommendation** — plus, for consults, the **cross-vendor signal** (did the
outside families agree with the internal council, or split?). Persistence is
deliberately thin: only a verdict that changes real execution truth gets a
decision node in the knowledge base; routine calls don't (see
`docs/wiki-protocol.md`).

## Who decides — the delegation boundary

Two rules close the protocol:

1. **The hive advises; the orchestrator decides.** Internal voices and
   external workers alike are advisors. The orchestrator forms its own
   position first, synthesizes, and **owns the verdict**. No external model
   makes the call.
2. **Architecture decisions are never delegated to workers.** In the routing
   taxonomy (`skills/delegate-external/`), `architecture_decision` maps to
   *self* — permanently. Workers execute scoped briefs; decisions with
   lasting structural consequences are made at the orchestrator level, or by
   the human. A consult is how the orchestrator borrows outside judgment
   *without* handing over the decision.

## See also

- `skills/council/` — the internal four-voice skill
- `skills/consult/` — council + mandatory cross-vendor review
- `skills/delegate-external/` — the dispatch mechanics consult rides on
- `docs/multi-runtime.md` — the fleet and routing model
- `docs/autonomous-runs.md` — how these gates slot into unsupervised runs
