---
type: note
tags: []
created: YYYY-MM-DD
status: draft
sources: []
edges:
  - to: ""
    rel: related_to
    weight: 0.5
---

# Node Title

> **TL;DR (≤80 words):** Cheapest possible answer to "what is this node about?" — the surface label of the graph node. Hard cap at 80 words; lint enforces.

## Connections

- [[Other Node]] *(rel, w=0.X)* — one-line reason for the edge

## Detail

Full content here. Loaded only when the TL;DR signals relevance to the agent's task.

---

**How to use this template:**

1. Copy the file. Rename to `<descriptive-slug>.md` and place it inside the active session-cluster folder (or `nodes/unsorted/` if no active cluster).
2. Set `type:` to one of the 17 types in `SCHEMA.md` §4. Default to `note` if unsure.
3. Replace the placeholder `edges:` block. Each edge needs `to:` (target wikilink target), `rel:` (one of 9 from §5), and `weight:` (0.0–1.0).
4. Write the TL;DR. ≤80 words. This is what other agents will read first.
5. Mirror the frontmatter `edges:` in the `## Connections` section so Obsidian's graph view picks up the wikilinks.
6. Write the Detail.

Delete this "How to use this template" section from the actual node — it's only here for reference inside the template file.
