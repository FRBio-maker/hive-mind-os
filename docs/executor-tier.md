# The Executor Tier — local models as decision-free workers

How a local, GPU-resident LLM fits the fleet as a **grunt-work executor** beneath
the decision-making agents.

The orchestration layer (`docs/multi-runtime.md`, and the routing in the tooling
repo) covers how the *decision-making* agents — the cloud CLIs — hand work to each
other. This document covers the layer **below** them: a cheap local model that does
high-volume, low-judgment work and makes no decisions of its own.

If the cloud agents are the colony's foragers and scouts, the executor tier is the
**drone ants** — they carry, they grind, they don't decide where the colony goes.

---

## Why a separate tier

The decision-making agents are expensive (per-token cost, rate limits) and powerful
(planning, tool use, judgment). A large class of fleet work needs neither the cost
nor the judgment:

- summarizing each item in a large backlog,
- a first-pass classifier or contradiction-detector over a knowledge graph,
- generating bounded narrative text grounded in figures you supply.

Routing that work to a cloud agent burns money and quota on jobs a 7–30B local model
does acceptably. The executor tier exists to **absorb that volume locally** — no
per-token cost, no data egress, no rate limit — while the decision-makers stay free
for the work that actually needs them.

**The hard rule: the executor never decides.** It receives a fully-specified prompt,
returns text, and is checked by the caller. It does not plan, route, choose tools, or
self-direct. The moment a task needs judgment, it goes up to a decision-making agent —
not down to the executor. This is what makes the tier safe to run unattended: a
worker with no autonomy can't take a wrong turn.

---

## The wiring pattern

The tier is just **a local server speaking an OpenAI-compatible HTTP API.** That one
choice is what makes it a drop-in: any consumer that can already call a hosted model
points its base URL at `localhost` instead.

```
  decision-making agent  ──hands scoped job──▶  consumer app
                                                     │
                                       OpenAI-style HTTP (localhost)
                                                     ▼
                                        local model server  ──▶  GGUF weights
                                        (llama.cpp / Ollama / vLLM / …)
```

- **Server:** any local runtime exposing `/v1/chat/completions` — `llama.cpp`'s
  `llama-server`, Ollama, vLLM, LM Studio, etc.
- **Consumers:** your apps call it through the standard OpenAI client, with the base
  URL pointed at the local server. No bespoke client code.
- **Cross-boundary reach:** if consumers run in a different namespace than the server
  (e.g. WSL apps reaching a Windows-side GPU server), bind the server to all
  interfaces and open the one port — don't proxy.

### A worked example (one deployment, not a requirement)

One concrete instance of this tier: a single `Qwen3-30B-A3B` MoE quantized to 4-bit,
served by `llama.cpp` on a **4 GB-VRAM** consumer GPU via **expert-offload** —
attention layers on the GPU, all mixture-of-experts layers on CPU/RAM. That fits a
30B-class model on hardware that can't normally hold it, at ~15 tokens/s. Slow for
chat, fine for multi-minute batch jobs. The point isn't this specific model — it's
that the tier can run a surprisingly capable model on modest hardware if the work is
batch-shaped and patient.

---

## What to send down vs. keep up

| Send to the executor | Keep on a decision-making agent |
|---|---|
| Bulk per-item summarization | Planning, multi-step reasoning |
| First-pass classification / tagging | Anything choosing a tool or next action |
| Pairwise "do these contradict?" checks | Final judgment calls with consequences |
| Bounded generation from supplied figures | Open-ended generation needing taste |
| Anything you'll verify programmatically | Anything you'd ship unverified |

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
  twice. Small local models self-correct well on a named fault.
- **Inject authoritative metadata.** Never trust the worker for identifiers, dates,
  or keys — overwrite those from your own records after generation.
- **Isolate failures.** In a batch, a single item's failure should mark that item and
  move on, never abort the run.

---

## Resilience

A local server is a process on a box — it dies, OOMs, or never started. The tier
needs a **lazy ensure-alive** guard: before a job, check the server is reachable;
if not, (re)launch it and wait for readiness, then proceed. Don't assume it's up.

Failure modes to plan for:

- **Orphaned server / OOM.** A stale process holding VRAM blocks the next launch.
  Kill strays before relaunch; cap concurrency to one model load.
- **Cold start.** First request after launch pays the weight-load cost (seconds to
  tens of seconds for large models with `--no-mmap`). Time out generously on the
  first call, tightly thereafter.
- **Context overflow.** Local models have hard context limits and degrade near them.
  When input exceeds the window, escalate that *one* job to a cloud tier rather than
  truncating and getting a confidently wrong answer.

---

## Tradeoffs, named

- **Cost vs. latency.** You trade money for wall-clock: free, but slow. Worth it for
  batch volume; wrong for anything a human is waiting on.
- **Privacy vs. capability.** Local means nothing leaves the box — good for sensitive
  corpora — but you cap out below frontier models. Keep the hardest work in the cloud.
- **One box vs. a fleet.** A single resident model is simple and cheap to operate but
  is a single point of contention. Fine at one-developer scale; revisit if many
  consumers contend for it.

---

## Companion, not shipped

Like the tooling repo and the approval relay, the executor tier is a **companion
component this template does not ship.** Bring your own local server; this document is
the pattern. The only thing worth version-controlling is the **tuned launch config**
(the offload split, KV-cache settings, context size, bind address) — keep that in a
small private repo. The weights and the build are regenerable and belong in neither.
