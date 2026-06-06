# LLM Wiki — vault template

This folder is a **starter vault** for the cross-agent knowledge wiki. Copy it
somewhere durable (e.g. `~/Obsidian/`), point your agents at it, and let the
graph accumulate. Everything here is vault-agnostic — no path is hardcoded.

## What this is

A **knowledge graph** an LLM agent builds and maintains on your behalf. Instead
of re-explaining things every conversation, the wiki accumulates concepts,
decisions, patterns, and synthesis as compounding artifacts. You browse it in
Obsidian; the agent does the writing and bookkeeping.

This vault is the **global meta-wiki** — knowledge that recurs across projects.
Project-specific knowledge lives inside each project's own `wiki/` folder,
scaffolded from `_templates/project-wiki/`.

## What makes it more than a plain Obsidian vault

1. **Every node has a short summary (≤80 words)** at the top — a cheap surface
   for the agent to scan before deciding whether to read the full content.
2. **Edges between nodes are typed and weighted** — the agent reasons about
   *why* nodes connect (`supports`, `contradicts`, `depends_on`, …), not just
   *that* they connect.
3. **Sessions cluster their nodes** — every agent conversation creates a folder
   of nodes with a summary, giving the wiki a temporal narrative as well as a
   topical one.

When the agent gathers context, it walks the graph in three tiers: cluster
summaries → in-cluster nodes → detail on demand. It stops the moment it has
enough. See `SCHEMA.md` §6.

## Requirements

Python 3.9+ is required to run the scripts. Install the small set of
dependencies before using them:

```bash
pip install -r scripts/requirements.txt
```

That installs PyYAML (used by `bind_clusters.py`) and pytest (for the test
suite). Everything else is standard library.

## Start your own vault here

1. **Copy this folder** to where you want the vault to live, e.g. `~/Obsidian/`.
   Open that folder as an Obsidian vault.
2. **Read `SCHEMA.md`** — the operating protocol. Node format, the 17-type
   taxonomy, the 9 edge types, three-tier traversal, and the workflows. This is
   the contract the agent follows.
3. **Create the working folders** the schema expects. The scaffolder does this
   for you:

   ```
   python scripts/scaffold.py --vault <path-to-your-vault>
   ```

   That creates `topics/`, `nodes/`, `_templates/`, and drops a copy of
   `SCHEMA.md` in place.
4. **Point your agents at it.** Set a `WIKI_ROOT` env var (or pass `--root`) so
   the scripts know where the vault lives — none of them assume a path.
5. **Work normally.** When a task touches durable files, the agent opens a
   session cluster (`nodes/<YYYY-MM-DD>-<slug>/`), files nodes as it goes, and
   binds them to topic hubs at the end. See `SCHEMA.md` §7 and §9.

## The scripts (in `scripts/`)

All read the vault root from `--root` / `WIKI_ROOT` (default: current dir), so
they run against any vault.

| Script | What it does |
|---|---|
| `gen_manifest.py` | Builds `MANIFEST.md` — the Layer-1 navigation backbone listing every topic hub and its TL;DR. The agent scans this on each message. |
| `bind_clusters.py` | Finds session clusters not yet bound to a topic hub and writes a `BINDING_QUEUE.md` backlog. |
| `lint_binding.py` | Exits non-zero when unbound clusters exist — a CI gate for wiki hygiene. |
| `scaffold.py` | Creates a new session cluster (`--slug`) or inits a fresh vault skeleton (`--vault`). |

Run the tests: `cd scripts && python -m pytest tests -v`.

## Templates (in `_templates/`)

- `node-template.md` — one knowledge node. Copy, rename to `<slug>.md`, fill in.
- `session-summary-template.md` — the `_summary.md` that anchors a session cluster.
- `project-wiki/` — the skeleton copied into a new `<project>/wiki/`.

## Don't usually write directly in here

You can, but the system is designed for the LLM to do the writing. Your job is
curating sources, asking questions, and reviewing what gets written. The agent
does the bookkeeping that makes a knowledge base actually useful over time.
