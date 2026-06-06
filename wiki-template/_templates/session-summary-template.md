---
type: session
tags: []
created: YYYY-MM-DD
status: draft
session_id: YYYY-MM-DD-<slug>
agent: 
duration_min: 
edges: []
---

# Session YYYY-MM-DD — <Topic>

> **TL;DR (≤80 words):** What this session worked on, what got produced, what got decided. The cheap surface of the cluster — agents read this first to decide whether to walk into the cluster's member nodes.

## Connections

*Edges to member nodes (`part_of`, this cluster ← member) and prior/related cluster summaries fill in here. Lint auto-adds the member-edges from folder containment.*

## Detail

### What was discussed

(Bullet points or brief paragraphs — the topics covered.)

### Nodes created or modified

- `[[<member-node-slug>]]` — one-line note on what it captures.

### Decisions made

- Decision X: rationale, alternatives considered.

### Open threads carried forward

- Question or thread that wasn't resolved this session.

---

**How to use this template:**

1. This file lives at `nodes/<YYYY-MM-DD>-<slug>/_summary.md` inside the session-cluster folder.
2. At session start, the agent creates this with `status: draft` and TL;DR = "in progress".
3. During the session, member nodes get added to the cluster folder, each with a `part_of` edge back to this `_summary.md`.
4. At session end, the agent finalizes the TL;DR, fills out the Detail sections, flips `status` to `stable`, adds cross-cluster edges, and updates `index.md` and `log.md`.

Delete this "How to use this template" section from the actual session summary — it's only here for reference.
