# Wiki Hygiene

How to keep the wiki graph accurate, connected, and non-contradictory over time.
This subsystem runs as a periodic "hygiene pass" and can be wired into a
session-end save routine.

Two components are **shipped** in `wiki-template/scripts/`. Two more are
**documented add-ons** — they are pure-Python or require a local LLM, and are
described here so adopters can wire them in.

---

## Shipped: manifest, binding queue, and coverage lint

### Manifest + agent binding

`wiki-template/scripts/` contains a script that generates a **title-only
manifest** of every topic hub in the vault. The manifest is a flat list of hub
names — cheap enough to inject into the agent's context at session start without
a meaningful context-window cost.

The binding rule injected alongside the manifest:

- On every user message, the agent scans the manifest.
- If any hub title is a plausible match for the current task, the agent walks
  that hub before answering (Tier 1 TL;DR first — see `docs/wiki-protocol.md`).
- If no hub matches, the agent announces "No manifest hits" and answers without
  walking the wiki.

The **binding queue** is a secondary output of the same script. It identifies
clusters (session-cluster folders) that have no `related_to: topics/*` edge in
their `_summary.md` frontmatter — orphans that were captured but never filed
under a topic hub. The queue gives the agent a concrete list to act on at
session end: add the missing edges, or flag the cluster for manual review.

### Binding lint

`wiki-template/scripts/lint_binding.py` is the **shipped** coverage gate. It
enforces exactly one rule and **exits non-zero on violation**, so it is CI-safe:
every session cluster must carry a `related_to topics/*` edge in its
`_summary.md` — no orphaned clusters. It shares its unbound-detection logic with
the binding-queue script, so "what counts as bound" has a single source of
truth. (This is the one rule the shipped script checks, and it is covered by the
repo's tests.)

Run it after any batch write, or wire it into a pre-commit hook / CI step.

The lint is deliberately minimal. Other structural invariants you may want — a
≤80-word TL;DR cap per node, a `_summary.md` in every cluster, a `## Current
truth` block on every project hub (see add-on below) — are easy to add as extra
checks, but are **not** enforced by the shipped script today. Add them as your
own conventions stabilise.

---

## Documented add-on: truth blocks

Not shipped — pure Python but coupled to the hub convention described here.
Adopters can implement this once they have a working vault with populated hubs.

### Hub classification

Every topic hub carries a `hub_kind` field in its YAML frontmatter:

```yaml
hub_kind: project   # active system — truth changes over time
# or
hub_kind: reference # stable fact / external concept — no truth block needed
```

### Current truth block

Every `project` hub must contain a `## Current truth (as of <DATE>)` section.
This section is a reconciled snapshot: the agent reads all clusters filed under
the hub and synthesises their findings into a single authoritative statement of
"what is true right now." It is not an append — it is a rewrite each time new
clusters change the picture.

The coverage lint enforces the invariant: `project` hub ⇒ truth block present;
`reference` hub ⇒ truth block absent. Violation exits non-zero.

### BOM gotcha

Files written by PowerShell's `Set-Content -Encoding utf8` carry a UTF-8 BOM
(byte-order mark) at the start of the file. Python's default `open()` will
surface this as a stray `﻿` character in the first line of frontmatter,
breaking YAML parsing. Any script that reads vault files on Windows must open
them with `encoding='utf-8-sig'` to strip the BOM transparently.

---

## Documented add-on: contradiction judge

Not shipped — requires a local LLM. This section describes the input contract
so adopters can wire their own judge.

### The problem

Two nodes may describe the same topic with conflicting facts. A naive diff
flags them as a contradiction. But many apparent conflicts are legitimate:
one node was superseded by a later one, or one is a continuation of the other.
A judge that cannot distinguish supersession from genuine conflict produces
too many false positives to be useful.

### Input contract

The judge receives, for each pair of flagged nodes:

- **Node A:** full text + frontmatter (including `date`, `status`, edge list).
- **Node B:** full text + frontmatter (including `date`, `status`, edge list).
- **Edges between them:** typed, weighted, directional — especially
  `followed_by`, `supersedes`, and `contradicts` if already asserted.

The judge must answer one of:

| Verdict | Meaning |
|---|---|
| `contradiction` | The two nodes assert incompatible facts with no supersession edge. |
| `supersession` | Node B explicitly follows from / replaces Node A — not a conflict. |
| `continuation` | The nodes describe different phases of the same truth — not a conflict. |
| `unclear` | Insufficient edge or date information to decide. |

Adopters supply the LLM call and any prompting; the schema above is the
interface contract. Feed the verdict back into the vault by adding a typed edge
(`contradicts` or `supersedes`) between the two nodes.

---

## Wiring hygiene into your workflow

The manifest regeneration, binding queue, and coverage lint can all run
automatically at session end — for example, as a step in a save routine that
also commits the vault and writes a session summary. The truth-block reconciliation
and contradiction judge are heavier (LLM calls) and are better run on-demand or
on a scheduled periodic pass rather than after every session.
