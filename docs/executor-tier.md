# The Executor Tier — cheap models as decision-free workers

How a cheap, high-volume LLM tier fits the fleet as a **grunt-work executor**
beneath the decision-making agents.

The orchestration layer (`docs/multi-runtime.md`, and the routing in the tooling
repo) covers how the *decision-making* agents — the cloud CLIs — hand work to each
other. This document covers the layer **below** them: a cheap model that does
high-volume, low-judgment work and makes no decisions of its own.

If the cloud agents are the colony's foragers and scouts, the executor tier is the
**drone ants** — they carry, they grind, they don't decide where the colony goes.

> **Doctrine change (2026-07):** the recommended executor tier is now a **hosted
> free/cheap-tier model API behind a small local proxy**, not a local model
> server. The local pattern remains documented below as an alternative for those
> with the hardware — the reasoning for the switch is in "Why hosted won".

---

## Why a separate tier

The decision-making agents are expensive (per-token cost, rate limits) and powerful
(planning, tool use, judgment). A large class of fleet work needs neither the cost
nor the judgment:

- summarizing each item in a large backlog,
- a first-pass classifier or contradiction-detector over a knowledge graph,
- generating bounded narrative text grounded in figures you supply.

Routing that work to a frontier agent burns money and quota on jobs a small,
cheap model does acceptably. The executor tier exists to **absorb that volume at
near-zero marginal cost** while the decision-makers stay free for the work that
actually needs them.

**The hard rule: the executor never decides.** It receives a fully-specified prompt,
returns text, and is checked by the caller. It does not plan, route, choose tools, or
self-direct. The moment a task needs judgment, it goes up to a decision-making agent —
not down to the executor. This is what makes the tier safe to run unattended: a
worker with no autonomy can't take a wrong turn.

---

## The recommended pattern: hosted cheap model + local proxy

The tier is a **free- or cheap-tier hosted model API** (example: Gemini Flash's
free tier; any provider with a generous cheap tier works) reached through a
**small local proxy** that all consumers point at:

```
  decision-making agent  ──hands scoped job──▶  consumer app
                                                     │
                                       OpenAI-style HTTP (localhost)
                                                     ▼
                                          local proxy (one process)
                                          • holds the API key
                                          • routes on the request's `model` field
                                          • paces requests under the rate limits
                                                     │
                                                     ▼
                                        hosted cheap-model API (provider)
```

The proxy is deliberately tiny — a single process on `127.0.0.1` — but it earns
its place three ways:

- **Key isolation.** The provider API key lives in exactly one process. Consumers
  never see it, never store it, never leak it into logs or repos. Rotating the key
  is a one-file change.
- **Routing on the `model` field.** Consumers send a standard chat request naming
  a model; the proxy maps that to the right provider and credentials. Swap the
  provider behind the tier and no consumer changes.
- **Pacing — a single choke point.** Free tiers come with rate limits (order of
  ~10 requests/min, ~1,000+ requests/day is typical). With many consumers hitting
  the provider directly, each would need its own backoff logic and they'd trip the
  limits collectively anyway. One proxy queues and paces globally, so batch jobs
  just run slower instead of failing.

### Why hosted won

The previous doctrine ran this tier locally (a quantized 30B-class model on a
consumer GPU). It works — *if you have the VRAM*. On modest hardware it fails in a
characteristic way: a model that doesn't fit in VRAM spills into system RAM, and a
30B model swapping through system RAM is slow enough to be unreliable in practice —
multi-minute latencies, watchdog timeouts, OOM kills. A hosted free tier gives you
a *more* capable model, zero VRAM, zero watchdog, zero cold-start, at zero marginal
cost — the only real payments are rate limits (the proxy paces those) and the
privacy tradeoff below.

### The tradeoff to name honestly: privacy

**Free tiers may train on your request content.** Read your provider's data-use
terms and assume the worst tier of them applies. The operating rule:

> **Never send secrets, credentials, or private/sensitive data to the executor
> tier.** Executor work should be content you'd be comfortable posting publicly:
> generic summarization, classification of non-sensitive text, bounded generation
> from figures you supply. Anything sensitive stays on a paid tier with a no-train
> guarantee, or on local hardware.

This is a *tier property*, not a bug — the tier is cheap because the provider gets
something from it. Route accordingly.

---

## The alternative: local inference (if you have the hardware)

Local serving remains a valid executor tier if you have real GPU headroom, and it
is the right choice when the work itself is sensitive (nothing leaves the box).
The wiring is the same shape — any local runtime exposing an OpenAI-compatible
`/v1/chat/completions` endpoint (`llama.cpp`'s `llama-server`, Ollama, vLLM,
LM Studio), with consumers pointing their base URL at `localhost`.

What to know before choosing it:

- **VRAM is the gate.** A model that fits entirely in VRAM is fast and reliable.
  Partial offload (attention on GPU, experts on CPU) can squeeze a 30B-class MoE
  onto a small GPU, but throughput drops to batch-only speeds and reliability
  drops with it. If the model must swap into system RAM, the tier will not be
  dependable — that failure mode is what moved the doctrine to hosted.
- **You own the resilience.** A local server is a process on a box — it dies,
  OOMs, or never started. You need a lazy ensure-alive guard (check reachable,
  relaunch, wait for readiness), stray-process cleanup before relaunch, generous
  first-call timeouts for cold weight loads, and escalation to a cloud tier when
  input exceeds the local context window.
- **What to version.** Only the tuned launch config (offload split, KV-cache
  settings, context size, bind address) — keep it in a small private repo. The
  weights and the build are regenerable and belong in neither.

---

## What to send down vs. keep up

| Send to the executor | Keep on a decision-making agent |
|---|---|
| Bulk per-item summarization | Planning, multi-step reasoning |
| First-pass classification / tagging | Anything choosing a tool or next action |
| Pairwise "do these contradict?" checks | Final judgment calls with consequences |
| Bounded generation from supplied figures | Open-ended generation needing taste |
| Anything you'll verify programmatically | Anything you'd ship unverified |
| — | **Anything containing secrets or private data** (hosted tier) |

Rule of thumb: if you can **write the grader for the output**, the executor can
produce it. If grading the output itself needs judgment, it's not executor work.

---

## Grounding and verification (don't trust the worker)

Because the executor is cheap and not very smart, treat every output as suspect and
check it in code:

- **Ground against the source, not the prompt.** If the model summarizes a
  figure-bearing document, verify the figures it emits against the *full* source —
  not the (possibly truncated) text you fed it. A figure that's real but lived in a
  section you trimmed for token budget must not be flagged as fabricated.
- **Retry with a corrective hint.** On a parse/validation/grounding failure, append
  the bad reply plus a specific correction to the message list and retry once or
  twice. Small models self-correct well on a named fault.
- **Inject authoritative metadata.** Never trust the worker for identifiers, dates,
  or keys — overwrite those from your own records after generation.
- **Isolate failures.** In a batch, a single item's failure should mark that item and
  move on, never abort the run.

---

## Resilience (hosted flavor)

The hosted tier removes the local server's failure modes and substitutes its own:

- **Rate-limit exhaustion.** The daily quota is a hard wall. The proxy should
  count requests, refuse (or queue overnight) past the budget, and report usage —
  don't let one runaway batch job silently eat the day's quota.
- **Provider outage / key revocation.** The proxy is the one place to detect it:
  fail loud with a clear error, never retry-storm the provider.
- **Model deprecation.** Providers retire model names. Because consumers route by
  the `model` field through the proxy, the fix is one mapping line, not a fleet
  edit.

---

## Tradeoffs, named

- **Hosted vs. local.** Hosted: more capable model, zero hardware, zero ops — but
  your request content leaves the box and may be trained on. Local: private and
  offline-capable — but VRAM-gated, slower, and you own the babysitting.
- **Cost vs. latency.** Free tiers trade throughput for money: pacing means batch
  jobs run over minutes-to-hours. Worth it for volume; wrong for anything a human
  is waiting on.
- **One proxy vs. direct calls.** The proxy is one more process to run, but it's
  the difference between one place holding the key + pacing and N consumers each
  doing it badly.

---

## Companion, not shipped

Like the tooling repo and the approval relay, the executor tier is a **companion
component this template does not ship.** Bring your own proxy (a few hundred lines
of stdlib Python suffices) and provider account; this document is the pattern. The
proxy config (model mappings, pacing budget, bind address) is worth
version-controlling in a small private repo — the API key is **not** (environment
or secret store only).
