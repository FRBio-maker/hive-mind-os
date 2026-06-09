# Memory Architecture

Three durable layers, modeled on how human memory actually works, plus an always-in-operation working-memory layer. They are **not redundant** — each plays a different role. Use the right layer for the right job.

## The three layers

### 1. Identity / preferences (auto-memory)

**Where:** `~/.claude/projects/<project>/memory/` (Claude); equivalent paths for other runtimes.
**Behavior:** Always loaded into context at session start. Small, deterministic, append-only across conversations.

Holds **who I am** and **how I work**. Things that should be true for every session in a project: user role, preferences, validated approaches, domain quirks. The identity file (e.g. `CLAUDE.md`) and per-project frontmatter are the long-lived public face; auto-memory is the more granular per-project bin.

**What goes here:** identity facts, feedback (corrections + confirmations), project status, reference pointers to external systems. NOT code patterns (derivable from the project state), NOT git history, NOT debugging recipes, NOT current task state (use a plan instead).

### 2. Schema / semantic (wiki vault)

**Where:** `<vault>/` (global) and `<project>/wiki/` (per-project).
**Behavior:** Curated, typed, walkable. The semantic layer — concepts, decisions, patterns. Walked on demand, summary-first traversal per the Wiki Protocol (see `docs/wiki-protocol.md`).

This is the **"I've gone down this trail before for this topic"** memory. When the current task has a topic anchor that may have prior work, the agent walks the graph via:
1. Cluster summaries (`_summary.md` per dated cluster).
2. In-cluster node summaries (frontmatter + TL;DR + Connections, ~30 lines each).
3. Detail on demand (full node only when relevance is confirmed).

Edge types and node taxonomy are formalized in `<vault>/SCHEMA.md` (17 node types, 9 edge types).

**What goes here:** durable knowledge that recurs across sessions. Concepts you'll consult repeatedly. Decisions with ADR-style rationale. Patterns observed across multiple instances. Playbooks for repeatable procedures.

### 3. Episodic record (episodic capture layer)

**Where:** Tool-dependent — e.g. an episodic capture tool such as claude-mem stores sessions at `~/.claude-mem/`.
**Behavior:** Full-fidelity capture of past sessions, automatically appended via PostToolUse + Stop hooks. The autobiographical record. Storage substrate, not curated structure.

Retrieval of episodic **content** is **cued, not eager**. One nuance to be precise about: a **compact digest** of recent observations (IDs + titles + timestamps — a navigation index, not the content) *is* injected at session start, the same way the wiki manifest is. What is **off by design** is auto-injection of the full observation *bodies* — those you pull explicitly when a topic anchor suggests prior work might exist (use a `mem-search` skill or equivalent tool). Treat it like a journal whose table of contents sits on the desk: the index is in front of you; you open the actual entry only when a cue tells you it's worth reading.

### The working-memory layer (context-mode)

**Where:** Context-mode MCP server (runs alongside the agent).
**Behavior:** Offloads large tool outputs (build logs, large file reads, browser snapshots) to a sandbox so they don't fill the agent's context window. Provides search and execute primitives over the sandbox.

This is a different *kind* of layer from the three above — it holds **working memory** (what fits in the active context window), not durable cross-session memory. But it is a **first-class, always-in-operation part of the stack, not an optional add-on**: large outputs route through it every session via a tool hook. Pairs with the three durable layers: routine outputs go to context-mode, durable findings get promoted to the wiki vault, identity-shaping observations get auto-memory entries.

## Layer-selection rules

| Want to remember... | Use layer |
|---|---|
| "The user prefers terse responses" | Auto-memory (identity) |
| "We chose folder-based IPC over HTTP because..." | Wiki vault (decision node) |
| "What did we try last Tuesday on the keyboard-clear bug?" | Episodic layer (cued query) |
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

## Why three core layers and not one big bag

Different lifecycles, different access patterns, different content shapes. Mixing them creates either token-explosion (loading everything every time) or retrieval failure (the right memory exists but the wrong layer is searched). Human memory works this way for the same reason — semantic / episodic / procedural memory are anatomically distinct in the brain. The working-memory layer (context-mode) is counted separately because it is a different *kind* of memory — always in operation, but managing context budget within a session rather than durable knowledge across sessions. A separate kind, not an optional one.

## Cross-references

- `docs/wiki-protocol.md` — the wiki traversal protocol (canonical for layer 2).
- `identity/CLAUDE.md` — Claude's identity file pointer into this protocol.
- `<vault>/SCHEMA.md` — full node taxonomy and edge type definitions.
