# LLM Wiki — Protocol Schema

This is the canonical operating protocol for the LLM Wiki. It applies to the global vault at `<vault>/` and to per-project wikis at `<project>/wiki/`. Read this document before writing or modifying nodes.

## 1. Architecture

The wiki has two layers:

- **Global meta-wiki** (`<vault>/`) — knowledge that recurs across projects (parts you reuse, libraries, generic concepts, cross-project decisions).
- **Per-project wiki** (`<project>/wiki/`) — knowledge specific to a single project. Travels with the code in git.

**Boundary rule (operational test):** *"Would this still be true in a new project that shares nothing else with this one?"*

- **Yes → global.** Generalizable principle, library behavior, hardware physics, recurring pattern.
- **No → project-local.** Tied to specific facts of this build (board, calibration, file layout, naming).

A project node can be promoted to global later — see §7 *Promotion workflow*.

## 2. Folder layout

Global vault:

```
<vault>/
├── README.md
├── SCHEMA.md                              ← this file
├── index.md                               ← catalog of clusters and topic hubs
├── log.md                                 ← chronological event log
├── _templates/
│   ├── node-template.md
│   ├── session-summary-template.md
│   └── project-wiki/                      ← scaffold copied into <project>/wiki/
├── nodes/
│   ├── <YYYY-MM-DD>-<slug>/               ← session cluster
│   │   ├── _summary.md                    ← cluster summary, type: session
│   │   └── ... member nodes ...
│   └── unsorted/                          ← ad-hoc captures awaiting placement
├── topics/                                ← topic-hub concept nodes (cross-cutting, durable)
│   └── <hub-slug>.md                      ← type: concept, ≥2 inbound references required (see §7 Promotion)
├── sources/                               ← raw imports + source nodes + sidecars (see §3)
│   ├── <slug>.pdf                         ← the external artifact
│   ├── <slug>.md                          ← source node (durable retrieval index)
│   ├── <slug>-toc.md                      ← TOC sidecar (auto-generated)
│   └── <slug>-text.md                     ← full-text sidecar (auto-generated, grep target)
└── assets/                                ← images (Obsidian Web Clipper target)
```

`topics/` holds topic-hub `concept` nodes — cross-cutting durables that have been consolidated from recurring patterns across session clusters. Entry requires ≥2 inbound references (see §7 *Promotion (concept → topics/)*). Flat layout; no nesting. Color family: Knowledge (teal) per §8.

Per-project wikis follow the same shape inside `<project>/wiki/`.

## 3. Node format

Every node is a markdown file. Order matters: navigation comes first so an agent can read just the file head cheaply.

```markdown
---
type: <one of 17 — see §4>
tags: [tag1, tag2]
created: YYYY-MM-DD
status: draft | stable | superseded
sources: [[sources/article-title]]
edges:
  - to: "Other Node"
    rel: <one of 9 — see §5>
    weight: 0.0–1.0
---

# Node Title

> **TL;DR (≤80 words):** Cheapest possible answer to "what is this node about?" — the surface label of the graph node. Hard cap. Lint enforces.

## Connections
- [[Other Node]] *(rel, w=0.X)* — one-line reason for the edge

## Detail
Full content. Loaded only when the TL;DR signals relevance.
```

**Two sources of edge data — kept in sync by lint.** Frontmatter `edges:` is canonical (machine-parseable, queryable). The `## Connections` section is auto-rendered from frontmatter for human reading and for Obsidian's graph view.

**Node size discipline:**

- TL;DR: ≤80 words. Hard. Lint enforces.
- Total node: target 50–300 lines. Past ~300 lines, lint suggests splitting into linked sub-nodes.

**Implicit cluster membership:** every node inside a session-cluster folder must have a `part_of` edge to that cluster's `_summary.md`. Lint auto-adds this if missing (folder containment is the trigger; frontmatter remains canonical).

**Source nodes live in `sources/`, not in session clusters.** A `source` node is a durable retrieval index into external semantic memory — it outlives the moment of ingest. File it as `sources/<slug>.md` alongside the artifact it indexes. The session cluster where ingest occurred records the *episode* of acquisition (via `_summary.md`); the durable artifact lives next to the brick. This is the only node type with a fixed home outside `nodes/`. All other node types follow the standard cluster-or-unsorted rule.

## 4. Node types (17)

Closed taxonomy. Use `custom` only after declaring the new type in this SCHEMA.md.

| Type           | Definition                                                                                                                                  | Decision rule                                                     |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **pillar**     | Foundational principle that should auto-inject into agent context for this domain. Rare, high-stakes.                                       | "If I want this remembered every session in this domain, pillar." |
| **decision**   | Concrete choice between alternatives. ADR-style: alternatives, rationale, date.                                                             | "Did I weigh A vs B and pick? Decision."                          |
| **concept**    | Defined term, framework, or model to reason from. Stable boundaries. **Also the type used for topic-hub nodes** (§6).                       | "Could this go in a glossary? Concept."                           |
| **question**   | Tracked unknown. Becomes `hypothesis` once falsifiable.                                                                                     | "I want to find out. Question."                                   |
| **playbook**   | Repeatable procedure: trigger, steps, expected outcome.                                                                                     | "Future-me would step through this. Playbook."                    |
| **task**       | Actionable item synced from a real task system. Has owner + status.                                                                         | "Has owner and status. Task."                                     |
| **event**      | Dated occurrence reasoned about temporally (launch, field test, milestone). Distinct from `session`.                                        | "Matters because of *when* it happened. Event."                   |
| **pattern**    | Empirical regularity observed across multiple instances. Heuristic, not law.                                                                | "Keeps happening. Pattern."                                       |
| **hypothesis** | Falsifiable prediction with measurable test and expected outcome.                                                                           | "I could be wrong measurably. Hypothesis."                        |
| **fact**       | Verified atomic statement, single source, dated.                                                                                            | "One sourced sentence true on a date. Fact."                      |
| **source**     | External reference (paper, article, datasheet) plus your synthesis.                                                                         | "Wraps one external doc. Source."                                 |
| **bookmark**   | Saved link, lightly annotated, not yet processed.                                                                                           | "Captured but not digested. Bookmark."                            |
| **note**       | Low-priority scratch. **Default for uncertain captures.**                                                                                   | "Don't know what kind of node this is yet. Note."                 |
| **contact**    | Person node with relationship metadata (role, expertise, last contact).                                                                     | "Is it a person? Contact."                                        |
| **reference**  | Pointer to a config, schema, or pinned doc. Stable, frequently consulted.                                                                   | "Canonical lookup I keep returning to. Reference."                |
| **session**    | The `_summary.md` node inside a session-cluster folder. Anchors the cluster, lists member nodes, links to sibling clusters. Auto-generated. | "Am I summarizing what a single session produced? Session."       |
| **custom**     | Workspace-specific type that doesn't fit. Must be declared in SCHEMA.md before use.                                                         | "None of the above and recurring. Declare it."                    |

**Default rule:** when uncertain, file as `note`. Lint suggests reclassification once the node has matured (gained edges, been referenced from other clusters, or exceeded a length threshold).

**Topic clusters use `concept` (not a new type):** when a theme recurs across multiple session-clusters (e.g. "websites," "motor control"), promote it by writing a `concept` node whose role is to link out to the relevant clusters and member nodes via `related_to` / `part_of` edges. A topic-hub *is* a concept. Lint flags candidates: "tag X appears across 3+ clusters — promote to a topic-hub concept?"

**Topic hubs carry a `hub_kind` frontmatter field — `project` or `reference`:**

- **`project`** — the hub tracks something with *evolving state* (built / retired / broken / in-progress): a subsystem you maintain, a named product, the wiki itself. These hubs carry a living `## Current truth (as of <date>)` block, reconciled at session-save time and stamped with `truth_reconciled`.
- **`reference`** — the hub *accumulates facts that don't reverse*: domain knowledge (a science field, a math area), literature hubs, and test fixtures. No truth block — a "state of the project" headline would be filler. New facts append; they don't supersede a project decision.

The field is what the tooling reads to decide whether a hub gets a truth block, so a bootstrap pass never has to re-judge by hand. A hygiene pass can stamp it across all hubs (the project set is the human judgment call; everything else defaults to `reference` and is reported for review). A `reference` hub that grows real evolving state can be promoted to `project` — add it to the set, re-run, then bootstrap its truth block.

## 5. Edge types (9)

| Edge | Direction | Semantic | Default weight |
|---|---|---|---|
| **supports** | A → B | A provides evidence for B. | 0.7 |
| **contradicts** | A ↔ B | A disagrees with or invalidates B. | 1.0 |
| **depends_on** | A → B | B must be true before A makes sense. | 0.8 |
| **derived_from** | A → B | A was created based on B (lineage). | 0.9 |
| **related_to** | A ↔ B | Topical connection, no stronger relationship known. | 0.5 |
| **part_of** | A → B | A is a component of B. | 0.8 |
| **preceded_by** | A → B | A comes after B in time. | 0.7 |
| **followed_by** | A → B | A comes before B in time. | 0.7 |
| **authored_by** | A → B | B is the author/originator of A. | 1.0 |

**Bidirectional edges** (`contradicts`, `related_to`) are written once on the source node; lint ensures the reverse exists on the target.

**Weights are starting defaults.** Tune per-edge when the relationship is unusually strong or weak. Weights drive prioritized traversal — when budget is tight, the agent walks higher-weight edges first.

## 6. Traversal protocol — three-tier summary-first

When gathering context for a task, walk the graph in three tiers, expanding only as needed.

**Tier 1 — find the relevant cluster(s).**
Scan cluster summaries (`_summary.md` of each session-cluster, plus topic-hub `concept` nodes). Each is cheap (TL;DR ≤80 words + edges). Cluster count stays in the dozens, not thousands.

**Tier 2 — scan in-cluster nodes.**
Within a relevant cluster, read frontmatter + TL;DR + Connections of each member node (~30 lines per node). Decide which need deeper reading.

**Tier 3 — read detail on demand.**
Only nodes whose TL;DR earned it get expanded into their `## Detail` section.

At each tier: walk highest-weight edges first when budget is tight. Stop the moment collected context is sufficient. **The graph is walked, not flooded.**

This protocol is the reason for every other constraint in this schema — the TL;DR cap, Connections-before-Detail, frontmatter edges with weights, the type taxonomy, cluster organization. Each piece exists to make three-tier traversal cheap and accurate.

## 7. Workflows

### Session ritual

**Session start** *(triggered per §9 — any task that will edit files in `<vault>/` or a tracked project repo):*

- Create `nodes/<YYYY-MM-DD>-<slug>/` (slug auto-derived from session topic).
- Write a placeholder `_summary.md` with TL;DR = "in progress" and `status: draft`.
- Announce the cluster slug in chat: *"Opening cluster `<slug>` for this work."*

**During session:**

- As concepts, decisions, patterns, etc. emerge, create them as files inside the session folder.
- Each new node gets a `part_of` edge back to `_summary.md`.
- Member node `created:` dates match the session date.

**Session end** (triggered by a session-end command, "summarize this session into the wiki", or the agent recognizing the session winding down):

- Finalize `_summary.md` with the real TL;DR + edges + Detail (what got produced, decisions made, open threads carried forward).
- `status` flips to `stable`.
- Update `index.md` with the new cluster.
- Append to `log.md`: `## [YYYY-MM-DD] session | <slug> — <one-line>`.
- Add cross-cluster edges (this cluster ↔ prior related cluster) to `_summary.md` if they exist.

### Ingest (a new source enters the wiki)

1. Drop the source into `sources/` (or `assets/` for images).
2. Run the ingest step for your toolkit: generate `<slug>-toc.md` and `<slug>-text.md` sidecars alongside the artifact and a stub `<slug>.md` source node with metadata frontmatter pre-filled.
3. A session cluster opens automatically per §9 Doer mode. Join an existing cluster if one is already open for related ingest work.
4. Edit the stub source node (`sources/<slug>.md`):
   - Fill TL;DR (≤80 words): what the source is, what domain it covers, why it's in the vault.
   - Fill Detail: synthesis-level summary, chapters/sections that matter for current work.
   - Confirm or correct metadata frontmatter (author, title, year).
5. Wire at least one topic-hub edge:
   - If a relevant `topics/<hub>.md` exists, add a `related_to` edge from the source node to it.
   - If no relevant hub exists, either create one (only if you can defensibly say it would be referenced from ≥2 sources or clusters — see *Promotion (concept → topics/)* below) or leave the source `unbound` and let the binding lint flag it on next run.
6. Append to `log.md`: `## [YYYY-MM-DD] ingest | <source slug>`.
7. The session cluster's `_summary.md` references the ingest with a brief member node or inline mention. The cluster captures the episode; the durable artifact lives in `sources/`.

### Query (answering a question)

1. Apply the three-tier traversal protocol (§6) against existing nodes.
2. Answer the user.
3. Classify the moment per §9 *Inclusion threshold*:
   - **Lookup** — single round-trip, no external source consulted, no multi-step synthesis. Append `## [YYYY-MM-DD] query | <question>` to `log.md`. No graph node. Declare: *"Logged as lookup, no node."*
   - **Research arc** — agent consulted an external source OR weighed alternatives across multiple turns. File: a `question` node (the topic), an answer node (`concept` / `fact` / `decision` / `hypothesis` per the synthesis), and `source` nodes for any literature consulted. Link per §5: question ←(`derived_from`)— answer; answer ←(`supports`)— sources. Update `index.md` if a new topic-hub is warranted. Declare: *"Filed as `question` + `<answer-type>` in cluster `<slug>`."*

### Promotion (project → global)

1. Identify a project-local node that's actually generalizable (boundary rule §1).
2. Move file: `<project>/wiki/nodes/<cluster>/<node>.md` → `<vault>/nodes/<cluster>/<node>.md` (or into a new cluster if appropriate).
3. Update edges: any references to the old path get rewritten.
4. Run lint to catch broken references.
5. Append to `log.md`: `## [YYYY-MM-DD] promote | <node>`.

### Promotion (concept → topics/)

A `concept` node born in a session cluster *migrates* to `topics/` once it has earned consolidation. This mirrors systems consolidation in the brain — patterns repeated across episodes get abstracted into stable cortical representations.

1. The binding lint (or a future general lint pass) identifies a `concept` node referenced from ≥2 session clusters OR ≥2 source nodes. Surfaces it as a promotion candidate.
2. User reviews and confirms.
3. File moves: `<birth-cluster>/<concept-slug>.md` → `topics/<concept-slug>.md`.
4. All inbound edges are rewritten to point at the new path.
5. Append to `log.md`: `## [YYYY-MM-DD] promote | <concept-slug>`.

**Demotion** is the inverse: a node in `topics/` whose inbound-edge count drops below 2 is flagged as a topic-hub orphan; user either re-links it or moves it back to its origin cluster (or to `_archive/`).

### Lint (periodic health check, including `--prune`)

**Structural checks:**

- TL;DR over 80 words → flag.
- Frontmatter `edges:` and `## Connections` section out of sync → flag.
- Missing reverse edge for `contradicts` / `related_to` → flag, offer to add.
- Member node missing `part_of` edge to its cluster `_summary.md` → auto-add.
- Nodes over ~300 lines → suggest splitting.
- `custom` types not declared in this SCHEMA.md → flag.

**Semantic checks:**

- Stale claims (newer source contradicts older without resolution) → flag.
- Orphan nodes (no inbound edges, ≥30 days old) → flag for prune.
- Tags appearing across 3+ session-clusters → suggest promotion to a topic-hub `concept` node.
- `unsorted/` nodes older than 14 days → prompt to file or archive.

**Prune mode (`lint --prune`):**

- Surfaces archive candidates: orphan nodes >30 days, superseded nodes, low-value `note` accumulations.
- Action is *move to `_archive/`*, not delete (reversible).
- Run on demand or monthly.

## 8. Color coding (Obsidian graph view)

Node colors are configured per type via Obsidian's graph view settings. Edge colors require a plugin (e.g. Juggl); without it, edge type is still visible in the rendered Connections section text.

Palette, grouped by family for legibility at a glance. One color per family (7 groups), not per type — easier to read than 17 colors. Hex codes live in `.obsidian/graph.json` under `colorGroups`; retune there.

| Family | Types | Hex | RGB int |
|---|---|---|---|
| Foundation | pillar, decision, reference | `#E55A4C` (warm red) | 15030860 |
| Knowledge | concept, pattern, fact | `#4FA8C7` (teal) | 5220551 |
| Inquiry | question, hypothesis | `#A875D6` (purple) | 11040214 |
| Process | playbook, task | `#6BC07A` (green) | 7061626 |
| External | source, bookmark, contact | `#C49770` (tan) | 12883824 |
| Temporal | event, session | `#888888` (gray) | 8947848 |
| Default | note, custom | `#BBBBBB` (light gray) | 12303291 |

**Design rationale (per family):**

- **Foundation** (warm red) — anchors. Pulls the eye first.
- **Knowledge** (teal) — stable, calm. The working knowledge layer.
- **Inquiry** (purple) — open / unresolved. Visually distinct from knowledge.
- **Process** (green) — action-oriented. "Go."
- **External** (tan) — outside material brought in.
- **Temporal** (gray) — containers, not content. Recede visually.
- **Default** (light gray) — low-priority / undecided. Recedes further.

**How matching works:** Obsidian color groups are search queries, not frontmatter readers. Each group's query is `"type: <X>" OR "type: <Y>" ...` with quoted exact-text matches against the file body — which catches the `type:` line in YAML frontmatter. First matching group wins, so groups are ordered specific → default.

## 9. Inclusion threshold — when work enters the wiki

Replaces silent agent judgment about whether work is "important enough" to record. Both triggers below are **observable** (what tools/files the agent used), not vibes. The user can audit compliance from git diffs + the agent's tool history.

### Doer mode — automatic clustering

Any task the user asks the agent to execute that edits a file in `<vault>/`, in a tracked project repo, or in durable global agent assets MUST open a session cluster. No agent discretion, no exceptions.

- At task start, the agent creates `nodes/<YYYY-MM-DD>-<slug>/_summary.md` (`status: draft`, TL;DR: "in progress") and announces the slug: *"Opening cluster `<slug>` for this work."*
- Durable artifacts produced during the task (`decision`, `pattern`, `playbook`, etc.) get filed as member nodes with `part_of` edges to `_summary.md`.
- At task end, the agent finalizes `_summary.md` and appends a `session` line to `log.md` per §7.

### Global agent assets extension

Global agent assets are durable files that change how future agents behave across projects. They count as Doer-mode triggers even when they live outside a normal project repo.

Examples:

- **Codex:** `.codex/AGENTS.md`, `.codex/config.toml`, `.codex/skills/**`, `.codex/plugins/**`, `.codex/rules/**`, durable Codex source/config/workflow assets.
- **Claude:** `.claude/CLAUDE.md`, `.claude/settings.json`, `.claude/hooks/**`, `.claude/skills/**`, `.claude/plugins/**`.
- **Gemini:** `.gemini/GEMINI.md`, `.gemini/settings.json`, `.gemini/policies/**`, `.gemini/config/**`, `.gemini/extensions/**`.
- **Shared agent infrastructure:** memory/index tooling, relay tooling, approval relay tooling, context-mode tooling.

Do not trigger on transient logs, package caches, generated session transcripts, or runtime state unless the task deliberately curates them into durable documentation.

**Source ingest is Doer mode.** Adding a file to `sources/`, `topics/`, or any wiki folder is a file edit and therefore opens a session cluster. There is no "silent ingest" path — the act of acquiring an external source is itself an episode worth encoding.

### Researcher mode — observable-action trigger

A research moment produces graph nodes only when the agent did at least one of:

- **Consulted an external source** — read a file in `sources/`, used a web fetch, opened a project file in service of an answer, etc.
- **Multi-turn synthesis** — weighed alternatives across more than one round-trip before answering.

When either trigger fires, the agent files:

- A `question` node — the topic researched.
- An answer node — type depends on what the synthesis yielded: `concept` (new defined term/framework), `fact` (single dated atomic claim), `decision` (a choice with alternatives), or `hypothesis` (falsifiable prediction).
- `source` nodes for any external literature consulted.
- Edges: question ←(`derived_from`)— answer; answer ←(`supports`)— sources.

When neither trigger fires — single round-trip answered from existing knowledge, no source touched — the question gets only a `log.md` line per §7 *Query*. No graph node.

### Where research nodes live

Default location: the active session cluster, if Doer mode is already running. If research happened outside any active session, nodes go in `unsorted/` and lint prompts placement.

When the same research topic recurs across ≥2 clusters, lint suggests promoting the question + answer into a topic-hub `concept` (§4).

### Agent declaration requirement

To keep the rule visible (not silent), the agent MUST announce, out loud, at these moments:

- **Start of any file-touching task:** *"Opening cluster `<slug>`."*
- **End of a research moment:** either *"Filed as `question` + `<answer-type>` in cluster `<slug>`"* or *"Logged as lookup, no node."*
- **When a moment that started as lookup becomes research mid-stream:** *"Promoting to research arc — will file nodes at end."*

The user can override any of these calls at any moment. Silent compliance ≠ compliance — the announcement is the rule.
