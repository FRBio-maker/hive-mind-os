# Wiki Traversal Protocol

How an agent navigates the knowledge wiki without flooding its context window.
This document covers the traversal protocol — the "how to walk the graph"
rules. The full node taxonomy, edge types, and authoring conventions live in
`<vault>/SCHEMA.md`.

---

## The core principle: the graph is walked, not flooded

The wiki can hold hundreds of nodes. Loading them all at session start would
consume the agent's entire attention window before any real work begins. The
protocol solves this with a three-tier, summary-first walk: read cheap surface
labels first, expand only what earns it.

---

## The three-tier walk

**Tier 1 — find the relevant cluster(s).**
Scan cluster summaries (`_summary.md` of each session-cluster) plus topic-hub
concept nodes. Each is cheap — a TL;DR capped at ≤80 words plus edges. Cluster
count stays in the dozens, not thousands.

**Tier 2 — scan in-cluster nodes.**
Within a relevant cluster, read frontmatter + TL;DR + Connections of each
member node (~30 lines per node). Decide which need deeper reading.

**Tier 3 — read detail on demand.**
Only nodes whose TL;DR earned it get expanded into their full `## Detail`
section.

At each tier: walk highest-weight edges first when budget is tight. Stop the
moment collected context is sufficient. **The graph is walked, not flooded.**

This protocol is the reason for every other constraint in the schema — the
TL;DR cap, Connections-before-Detail ordering, frontmatter edges with weights,
the type taxonomy, session-cluster organization. Each piece exists to make
three-tier traversal cheap and accurate.

---

## TL;DR cap — ≤80 words, hard

Every node must open with:

```markdown
> **TL;DR (≤80 words):** Cheapest possible answer to "what is this node about?"
```

This is the surface label of the graph node. It is what the agent reads at
Tier 1 and 2 to decide whether to expand. If the TL;DR exceeds 80 words, the
promise of cheap scanning breaks. Lint enforces the cap.

---

## Typed, weighted, directional edges

Edges between nodes carry three pieces of information:

- **Type** — the semantic relationship (e.g. `supports`, `contradicts`,
  `depends_on`, `derived_from`, `related_to`, `part_of`, `preceded_by`,
  `followed_by`, `authored_by`). Nine types are defined in `<vault>/SCHEMA.md §5`.
- **Weight** (0.0–1.0) — how strong the relationship is. Drives traversal
  priority: when budget is tight, walk higher-weight edges first.
- **Direction** — most edges are directed (A → B). Bidirectional edges
  (`contradicts`, `related_to`) are written once and mirrored by lint.

Edge data lives in two places, kept in sync:
- **Frontmatter `edges:`** — canonical, machine-parseable.
- **`## Connections` section** — rendered from frontmatter for human reading
  and Obsidian graph view.

---

## Session-cluster organization

Every agent work session that edits tracked files produces a **session cluster**
— a folder of nodes under `<vault>/nodes/<YYYY-MM-DD>-<slug>/`.

**Opening a cluster (Doer mode):**
Any task that edits a file in the wiki vault, a tracked project repo, or a
durable global agent asset (identity files, hooks, skills, relay tooling) MUST
open a session cluster. No agent discretion.

- Create `nodes/<YYYY-MM-DD>-<slug>/_summary.md` with `status: draft` and
  TL;DR: "in progress".
- Announce the slug: *"Opening cluster `<slug>` for this work."*

**During the session:**
- File durable artifacts (decisions, patterns, playbooks) as member nodes inside
  the cluster folder.
- Each member node gets a `part_of` edge back to `_summary.md`.

**Closing a cluster:**
- Finalize `_summary.md` with the real TL;DR, edges, and a Detail section
  summarizing what got produced, decisions made, open threads.
- Flip `status` to `stable`.
- Update `index.md` and append to `log.md`.

**When finalizing, scan topic hubs.** Add `related_to` edges in frontmatter
for each hub this session's work touched (primary weight 0.8, secondary 0.5,
tertiary 0.3). Announce: *"Filed cluster under: [topics/X], [topics/Y]."*
If no hub fits, announce: *"No hub fits — left unbound for lint."*

---

## Manifest-first session start

At the start of any session, the agent scans the wiki manifest
(`<vault>/MANIFEST.md`) — a Layer-1 navigation backbone listing all topic hubs
and recent clusters. This is injected automatically if session hooks are wired;
otherwise the agent reads it manually.

On every user message, before answering, the agent asks: *"could any hub's
accumulated decisions, patterns, or edge cases sharpen my answer?"* If yes —
that is a manifest hit — the agent reads those hub TL;DRs before answering.

The agent announces one of:
- *"Manifest hit: [topics/X], [topics/Y] — reading TL;DRs."* Then reads those
  TL;DRs (and Connections) before answering. From there, walks deeper per the
  three-tier protocol only as far as needed.
- *"No manifest hits — no wiki walk."* Then answers without walking the wiki.

The announcement is the rule. Silent intuition is not compliance. "No hit" is
reserved for prompts clearly outside the vault's scope (shell tasks, generic
syntax, meta questions about the agent itself).

---

## Research moments and the query / research-arc distinction

Not every question warrants a new wiki node. The dividing line is observable:

**Lookup** — single round-trip, no external source consulted, no multi-turn
synthesis. Append one line to `log.md` as a `query` event. No graph node.
Declare: *"Logged as lookup, no node."*

**Research arc** — agent consulted an external source OR weighed alternatives
across multiple turns. File:
- A `question` node (the topic researched).
- An answer node — type depends on what synthesis yielded: `concept` (new
  defined term), `fact` (single dated atomic claim), `decision` (choice with
  alternatives), or `hypothesis` (falsifiable prediction).
- `source` nodes for any external literature consulted.
- Edges: `question` ←(`derived_from`)— `answer`; `answer` ←(`supports`)—
  `sources`.

Declare: *"Filed as `question` + `<answer-type>` in cluster `<slug>`."*

The trigger is what tools the agent used (external fetches, source-file reads,
turn count), not the agent's judgment of "is this worth keeping."

---

## Agent declaration requirement

To keep the protocol visible (not silent), the agent MUST announce out loud at
these moments:

- **Start of any file-touching task:** *"Opening cluster `<slug>`."*
- **End of a research moment:** either *"Filed as `question` + `<answer-type>`
  in cluster `<slug>`"* or *"Logged as lookup, no node."*
- **When a lookup becomes research mid-stream:** *"Promoting to research arc —
  will file nodes at end."*

The user can override any of these calls at any moment.

---

## Further reading

- `<vault>/SCHEMA.md` — the full formal taxonomy: 17 node types, 9 edge types,
  color coding, lint rules, promotion workflows, ingest workflow.
- `<vault>/README.md` — orientation guide for browsing the vault.
- `docs/memory-architecture.md` — where the wiki fits in the broader memory model.
