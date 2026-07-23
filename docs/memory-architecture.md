# Memory Architecture

Two durable layers plus an always-in-operation working-memory layer. They are
**not redundant** — each plays a different role. Use the right layer for the
right job.

> **Doctrine change (2026-07):** this used to be *three* durable layers. The
> third — an episodic capture layer (claude-mem) — was audited and **retired**.
> The evidence and the lessons are documented at the bottom of this file,
> because the subtraction taught us more than the layer ever did.

## The layers

### 1. Identity / preferences (auto-memory)

**Where:** `~/.claude/projects/<project>/memory/` (Claude); equivalent paths for other runtimes.
**Behavior:** Always loaded into context at session start. Small, deterministic, append-only across conversations.

Holds **who I am** and **how I work**. Things that should be true for every session in a project: user role, preferences, validated approaches, domain quirks. The identity file (e.g. `CLAUDE.md`) and per-project frontmatter are the long-lived public face; auto-memory is the more granular per-project bin.

**What goes here:** identity facts, feedback (corrections + confirmations), durable cross-project reference pointers. NOT project status — that lives in the wiki's topic hubs (see below). NOT code patterns (derivable from the project state), NOT git history, NOT debugging recipes, NOT current task state (use a plan instead).

### 2. Schema / semantic (wiki vault) — the source of truth for project state

**Where:** `<vault>/` (global) and `<project>/wiki/` (per-project).
**Behavior:** Curated, typed, walkable. The semantic layer — concepts, decisions, patterns, *and the single narrative record of ongoing work*. Walked on demand, summary-first traversal per the Wiki Protocol (see `docs/wiki-protocol.md`).

This layer is **also the episodic record**: dated session clusters
(`nodes/<date>-<slug>/`) capture what each work session did, curated at
checkpoint time rather than recorded automatically. When the automatic episodic
layer was retired (see below), these clusters were what had been carrying the
real session-recap role all along.

This is the **"I've gone down this trail before for this topic"** memory. When the current task has a topic anchor that may have prior work, the agent walks the graph via:
1. Cluster summaries (`_summary.md` per dated cluster).
2. In-cluster node summaries (frontmatter + TL;DR + Connections, ~30 lines each).
3. Detail on demand (full node only when relevance is confirmed).

Edge types and node taxonomy are formalized in `<vault>/SCHEMA.md` (17 node types, 9 edge types).

**What goes here:** durable knowledge that recurs across sessions. Concepts you'll consult repeatedly. Decisions with ADR-style rationale. Patterns observed across multiple instances. Playbooks for repeatable procedures. **Topic hubs are the authoritative "current state" of every active project** — when the episodic layer was retired, hubs-as-truth is the doctrine that replaced it.

### The working-memory layer (context-mode)

**Where:** Context-mode MCP server (runs alongside the agent).
**Behavior:** Offloads large tool outputs (build logs, large file reads, browser snapshots) to a sandbox so they don't fill the agent's context window. Provides search and execute primitives over the sandbox.

This is a different *kind* of layer from the two above — it holds **working memory** (what fits in the active context window), not durable cross-session memory. But it is a **first-class, always-in-operation part of the stack, not an optional add-on**: large outputs route through it every session via a tool hook. Pairs with the durable layers: routine outputs go to context-mode, durable findings get promoted to the wiki vault, identity-shaping observations get auto-memory entries.

## Checkpointing — how session state reaches the durable layers

Two durable layers only work if sessions actually flush into them. That flush
is a **defined, automatable workflow**, not a habit:

- **`/save`** — the full end-of-session checkpoint: finalize the session
  cluster (`_summary.md` draft → stable), reconcile the touched topic hub's
  current-truth block, regenerate the manifest, run the binding lint, and
  commit the vault. This is Tier-1 hygiene firing at the moment drift is
  created (see `docs/hygiene.md`).
- **`/quicksave`** — the mid-session subset: flush working state into the wiki
  nodes (cluster + touched nodes) **without** the git/finalize machinery.
  Cheap enough to run whenever meaningful state has accumulated.

(Two commands, not three: an earlier `/reset` variant — save + signal a context
reset — was folded into `/save`, since every full checkpoint should leave the
wiki resumable anyway.)

**Automate the trigger.** Relying on the agent (or the human) to *remember* to
checkpoint fails exactly when it matters — deep in a long session. The
reference implementation wires a hook that fires an automatic `/quicksave`
when **~30% of the context window is used**: state reaches disk before the
window gets tight, every time, with no one in the loop. This is the
automation-first principle applied to memory: each stage triggers the next
without a human remembering it.

## Layer-selection rules

| Want to remember... | Use layer |
|---|---|
| "The user prefers terse responses" | Auto-memory (identity) |
| "We chose folder-based IPC over HTTP because..." | Wiki vault (decision node) |
| "What did we try last Tuesday on the keyboard-clear bug?" | Wiki vault (session clusters — the `/save` layer) |
| "The current state of project X" | Wiki vault (topic hub current-truth block) |
| "The current state of file foo.py" | None — read the file |
| "All the build output from this CI run" | context-mode |

## What NOT to store anywhere persistent

These are derivable or ephemeral and don't belong in any memory layer:

- Code patterns, conventions, file paths, project structure (read the code)
- Git history, recent changes, blame (use `git log`)
- Current task state, in-progress work (use a plan / todo)
- Debugging recipes (the fix is in the code; the why is in the commit message)
- Anything already in a `CLAUDE.md` / `AGENTS.md` / `GEMINI.md` (those are auto-loaded)

This rule applies even when the user explicitly asks to save — if they want to "save the PR list," ask what was *surprising* or *non-obvious* about it. That's the durable part.

## Why two layers and not one big bag

Different lifecycles, different access patterns, different content shapes. Mixing them creates either token-explosion (loading everything every time) or retrieval failure (the right memory exists but the wrong layer is searched). The working-memory layer (context-mode) is counted separately because it is a different *kind* of memory — always in operation, but managing context budget within a session rather than durable knowledge across sessions. A separate kind, not an optional one.

## The retired third layer — episodic capture, and why it went

Until 2026-07 this doctrine had a third durable layer: an **episodic capture
tool** (claude-mem) that recorded every session full-fidelity via
PostToolUse/Stop hooks and injected a compact digest at session start. It was
retired after a whole-system audit. The findings generalize, so they stay in
the doctrine:

**Why it was retired:**

- **It failed the load-bearing test.** Its capture pipeline broke and ran
  broken for **10 days before anyone noticed — with zero operational
  impact**. Nothing downstream degraded. A memory layer whose absence changes
  nothing is not a memory layer; it's a write-only log with a token bill.
- **Write amplification.** The audit found the same session state being
  written 5–8× across four overlapping layers (episodic capture, auto-memory,
  wiki clusters, conversation summaries) — layers that already contradicted
  each other. The wiki's `/save` clusters were carrying the real
  session-recap role; the episodic record duplicated it, less curated.
- **Standing costs.** Session-start injection tokens, per-tool-call hook
  latency, a watchdog to keep its worker alive, and gigabytes of cache — all
  for a layer nothing depended on.

The databases were **archived read-only** (`~/.claude-mem-archive/`), not
deleted — subtraction doesn't require destruction.

**Lesson 1 — layers must earn their keep.** The test is subtraction: if a
layer can silently fail for days with no symptom, either instrument it (see
`docs/observability.md`) or remove it. Audit before adding a new layer, and
re-audit the ones you have.

**Lesson 2 — a doc-layer retirement isn't a decommission.** Declaring the
layer dead in the docs left it half-alive for weeks: the installed-plugin
record kept loading it, a scheduled-task watchdog kept resurrecting its
worker, and a marketplace `autoUpdate` flag kept re-cloning it daily. Tearing
down a layer means hunting every *moving part* — plugin records, scheduled
tasks, hooks, auto-updaters, caches — on **every** OS/runtime in the fleet,
not editing the doctrine file.

**If you still want one:** episodic capture can be worth running early, when
your wiki discipline isn't established yet. If you do: injection must be
digest-only (IDs + titles, never bodies), retrieval cued rather than eager,
and you should schedule the audit that decides whether it's load-bearing.

## Cross-references

- `docs/wiki-protocol.md` — the wiki traversal protocol (canonical for layer 2).
- `docs/hygiene.md` — the save-time reconcile workflow that keeps hubs truthful.
- `docs/observability.md` — how silent layer failure gets caught (the dashboard).
- `identity/CLAUDE.md` — Claude's identity file pointer into this protocol.
- `<vault>/SCHEMA.md` — full node taxonomy and edge type definitions.
