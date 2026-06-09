# Wiki Hygiene

How to keep the wiki graph accurate, connected, and non-contradictory as
sessions accumulate. Left unmaintained, a knowledge graph rots in three ways:
clusters get captured but never filed under a topic (orphans), hubs drift out of
date as later work supersedes earlier work, and two nodes end up asserting
incompatible facts with no edge marking the conflict. Hygiene is the correctness
layer that fights all three.

---

## The two-tier architecture

Hygiene is split into two tiers, deliberately mapped to how the system actually
runs. Most knowledge changes at the moment a work session ends — so the primary,
precise check fires there — while a coarser periodic pass catches the drift that
a per-session check structurally cannot see.

**Tier 1 — write-time, at session save (primary).**
When a session that touched the graph is finalized, reconcile the affected topic
hub against the cluster just produced: rewrite the hub's "current truth" to fold
in what changed, and bind any orphaned cluster to its hub. Precise, scoped to
exactly what changed, gated by a diff a human confirms. This is where most drift
is caught, because this is where most drift is *created*.

**Tier 2 — periodic sweep (safety net).**
A scheduled pass over the whole graph catches the long-range, cross-cluster drift
Tier 1 can't see: two nodes in different clusters that contradict each other but
were never edged together, so no single save ever compared them. Coarser and
heavier (it re-examines the whole graph), so it runs on a cadence — weekly or
on-demand — not after every session. **Flag-only:** it never edits content, only
marks suspect nodes for human review.

The division of labor is the point. Tier 1 is precise but **local** — it only
sees the cluster being saved. Tier 2 is global but **coarse** — it sees
everything, cheaply. Together they cover both the common case and the long tail.

---

## What ships here vs. what you wire

This template ships the **structural** half of hygiene — the parts that need no
LLM and no judgment. The **semantic** half (truth reconciliation and
contradiction judging) needs a model, so it is documented here as input-contracts
you wire to whatever LLM you run (a local model is plenty — see
`docs/executor-tier.md`).

| Capability | Tier | Status |
|---|---|---|
| Title-only manifest generation | — | **shipped** (`gen_manifest.py`) |
| Binding queue (orphan-cluster finder) | 1 | **shipped** (`bind_clusters.py`) |
| Binding lint (CI gate) | 1 | **shipped** (`lint_binding.py`) |
| Per-hub "current truth" reconcile | 1 | documented add-on (needs LLM) |
| Contradiction judge | 2 | documented add-on (needs LLM) |

---

## Shipped: manifest, binding queue, and coverage lint

### Manifest + agent binding

`wiki-template/scripts/gen_manifest.py` generates a **title-only manifest** of
every topic hub in the vault — a flat list of hub names cheap enough to inject
into the agent's context at session start without a meaningful context-window
cost. The binding rule injected alongside it:

- On every user message, the agent scans the manifest.
- If any hub title plausibly matches the current task, the agent walks that hub
  before answering (Tier 1 TL;DR first — see `docs/wiki-protocol.md`).
- If no hub matches, the agent announces "No manifest hits" and answers without
  walking the wiki.

### Binding queue

`bind_clusters.py` is the orphan finder: it identifies session clusters whose
`_summary.md` frontmatter has no `related_to: topics/*` edge — captured but never
filed under a hub. The queue gives the agent a concrete list to act on at session
end: add the missing edges, or flag the cluster for manual review.

### Binding lint

`lint_binding.py` is the **shipped** coverage gate. It enforces exactly one rule
and **exits non-zero on violation**, so it is CI-safe: every session cluster must
carry a `related_to topics/*` edge in its `_summary.md` — no orphaned clusters.
It shares its unbound-detection logic with the binding-queue script, so "what
counts as bound" has a single source of truth.

Run it after any batch write, or wire it into a pre-commit hook / CI step. The
lint is deliberately minimal — other invariants you may want (a ≤80-word TL;DR
cap, a `_summary.md` in every cluster, a current-truth block on every project
hub) are easy to add as extra checks but are **not** enforced by the shipped
script today. Add them as your own conventions stabilise.

---

## Documented add-on: current-truth blocks (Tier 1, semantic)

Not shipped — pure Python, but coupled to the hub convention described here.
Implement it once you have a working vault with populated hubs.

### Hub classification

Every topic hub carries a `hub_kind` field in its YAML frontmatter:

```yaml
hub_kind: project   # active system — truth changes over time
# or
hub_kind: reference # stable fact / external concept — no truth block needed
```

### Current truth block

Every `project` hub contains a `## Current truth (as of <DATE>)` section: a
reconciled snapshot synthesising every cluster filed under the hub into a single
authoritative statement of "what is true right now," with a `truth_reconciled`
date stamp. It is **not an append — it is a rewrite** each time new clusters
change the picture. At Tier 1 the agent regenerates only the touched hub's block,
and the human confirms the diff before it lands.

A coverage lint can enforce the invariant: `project` hub ⇒ truth block present;
`reference` hub ⇒ truth block absent. The engine split that keeps this safe: the
**LLM decides what is true; thin Python does the string-surgery** of swapping the
block in. Never let the model free-write into the file.

### BOM gotcha

Files written by PowerShell's `Set-Content -Encoding utf8` carry a UTF-8 BOM
(byte-order mark) at the start. Python's default `open()` surfaces this as a stray
`﻿` character in the first line of frontmatter, breaking YAML parsing. Any script
that reads vault files on Windows must open them with `encoding='utf-8-sig'` to
strip the BOM transparently.

---

## Documented add-on: the contradiction judge (Tier 2, semantic)

Not shipped — requires a local LLM. This section describes the input contract so
you can wire your own.

### The problem

Two nodes may describe the same topic with conflicting facts. A naive diff flags
them as a contradiction. But many apparent conflicts are legitimate: one node was
superseded by a later one, or one is a continuation of the other. A judge that
cannot tell supersession from genuine conflict produces too many false positives
to be useful.

### The key insight — fix the input contract, not the model

The judge's quality is bottlenecked by **what it is shown, not how big it is.** A
judge handed only the two node *bodies* cannot distinguish a real contradiction
from a legitimate supersession or continuation. The fix that makes a small local
model reliable is a richer input: feed it the **typed, dated, directional edges**
between the two nodes (`followed_by`, `supersedes`, `contradicts`) plus each
node's date and status. With that context it reliably separates "A was later
replaced by B" (not a conflict) from "A and B assert incompatible facts with
nothing connecting them" (a real conflict to flag). This is the single most
important design lesson of the subsystem — and the reason the executor-tier local
model is enough; you do not need a frontier model to judge.

### Input contract

For each pair of related nodes the judge receives:

- **Node A:** full text + frontmatter (including `date`, `status`, edge list).
- **Node B:** full text + frontmatter (including `date`, `status`, edge list).
- **Edges between them:** typed, weighted, directional — especially
  `followed_by`, `supersedes`, and `contradicts` if already asserted.

It answers one of:

| Verdict | Meaning |
|---|---|
| `contradiction` | The two nodes assert incompatible facts with no supersession edge. |
| `supersession` | Node B explicitly follows from / replaces Node A — not a conflict. |
| `continuation` | The nodes describe different phases of the same truth — not a conflict. |
| `unclear` | Insufficient edge or date information to decide. |

### Flag, never delete

The judge only ever **marks** a suspect node (a frontmatter `hygiene_flag` + a
dated report) and at most proposes a typed edge for a human to confirm. It never
rewrites or deletes content, and if the model is unreachable it writes nothing and
exits clean. A correctness layer that can silently mutate the graph is more
dangerous than the drift it fixes.

---

## Wiring hygiene into your workflow

**Tier 1** runs at session-end / save — fast and deterministic for the shipped
parts, plus one gated LLM call for the truth reconcile. A reference save routine:

1. regenerate the manifest (`gen_manifest.py`),
2. rebind orphans (`bind_clusters.py`),
3. run the binding lint (`lint_binding.py` — fails the commit if any cluster is
   unbound),
4. reconcile the touched hub's current truth (gated diff the human confirms),
5. commit the vault + write a session summary.

**Tier 2** (the contradiction sweep) is heavier and runs on a schedule or on
demand — point it at **cross-hub** pairs, the long-range drift Tier 1 structurally
leaves behind. Flag-only, resumable, never destructive. A dry-run pass over the
real vault before the first live run is strongly recommended.
