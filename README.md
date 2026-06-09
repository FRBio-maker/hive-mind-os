# hive-mind-os

> A markdown-and-config operating doctrine for running a cross-agent
> "hive mind" — one knowledge system and one set of operating rules shared
> across Claude Code, Codex CLI, Gemini CLI, and Grok. Not a Python project;
> a small Python toolkit supports a system whose primary medium is text.

**New here?** Read **[START-HERE.md](START-HERE.md)** first — what you get vs.
what you wire, in one page.

## What this is

`hive-mind-os` is an **operating doctrine** — a set of markdown files and
configuration templates that wire multiple AI runtimes into a single coherent
system. Each agent gets its own identity file (`identity/`), permission rules
(`permissions/`), and config template (`config-templates/`), all pointing at a
shared knowledge wiki built from `wiki-template/`.

What the system provides:

- **One wiki, many agents.** Every runtime reads and writes the same
  Obsidian-style vault. Decisions, patterns, and research accumulate in one
  place, not scattered across per-agent scratch pads.
- **Layered memory.** Identity preferences are always loaded; the wiki manifest
  is loaded on session start; episodic history is retrieved on cue. Nothing is
  auto-flooded into context.
- **Permission doctrine.** Every tool call passes through a permission resolver.
  Risky actions escalate to a human relay rather than auto-approving. The policy
  files in `permissions/` make the rules explicit and version-controlled.
- **Human-in-the-loop.** When no one is at the keyboard, agents send approval
  requests out-of-band (phone relay) and block until answered. They never
  silently proceed with irreversible actions.
- **Bootstrap installer.** `bootstrap/setup-linux.sh` and
  `bootstrap/setup-windows.ps1` copy or symlink the four **identity files** into
  the right runtime directories in one command. It does **only** the identity
  files — merging permission excerpts and symlinking the companion tooling are
  separate steps (see ONBOARDING.md).

## Philosophy

**Text-first.** Markdown is the medium; Python is the assistant. The doctrine
lives in plain files that any editor, diff tool, or agent can read without a
runtime dependency. Code is only introduced when markdown is insufficient.

**Cross-runtime by design.** No agent's *rules or memory* are privileged:
Claude, Codex, Gemini, and Grok share the same wiki, the same permission
pipeline, and the same house rules. Claude takes the orchestrator role, but
that's a division of labor, not a privileged ruleset. Identity files differ by
runtime; the operating doctrine does not.

**Summary-first traversal.** The wiki graph is *walked*, not flooded. Agents
read cluster summaries before nodes, node summaries before detail. Context
budget is spent on what the task actually needs.

**Human-in-the-loop for risky actions.** Irreversible or high-impact tool calls
require explicit human approval. The relay mechanism ensures this works even
when the human is away from the keyboard.

**Dry-run by default.** The bootstrap installer prints its plan before writing
anything. Writes require `--apply`; overwrites require `--force`. No surprises.

## Quickstart

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/hive-mind-os.git ~/hive-mind-os
cd ~/hive-mind-os

# 2. Run the bootstrap installer (dry-run first — prints plan, writes nothing)
bash bootstrap/setup-linux.sh
# On Windows (PowerShell):
#   pwsh bootstrap/setup-windows.ps1

# 3. Apply when you are happy with the plan
bash bootstrap/setup-linux.sh --apply
# pwsh bootstrap/setup-windows.ps1 --apply

# 4. Edit your identity
#    Open each identity/ file and replace the '# Who I am' placeholder
#    with your real agent persona.
$EDITOR identity/CLAUDE.md
$EDITOR identity/AGENTS.md   # Codex
$EDITOR identity/GEMINI.md
$EDITOR identity/GROK.md

# 5. Start a wiki vault
python3 wiki-template/scripts/scaffold.py --vault ~/my-project/wiki
```

> **Flags:** `--apply` to write files; `--force` to overwrite existing ones.
> Without `--apply` the installer only prints what it would do.

See [ONBOARDING.md](ONBOARDING.md) for the agent-facing walkthrough.

## The system at a glance

The full architecture — symlink topology, memory layers, permission pipeline,
approval relay, and skill routing — is documented with seven Mermaid diagrams
in [`docs/INFRASTRUCTURE.md`](docs/INFRASTRUCTURE.md).

Short version: each runtime directory (`~/.claude/`, `~/.codex/`, `~/.gemini/`,
`~/.grok/`) holds a symlink to the identity file in this repo — and **that is
all the bootstrap installs**. Permission settings are meant to be merged (not
symlinked) so the live file can hold machine-specific keys alongside the
versioned permission keys, but that merge is a **manual step you perform** using
the excerpts in `permissions/` — the bootstrap does not touch settings, hooks,
or permissions. Everything else — hooks, skills, plugins — is tree-symlinked
from a companion **tooling repo** (a separate repository that holds runnable
executables, hooks, and shared skills; **not included in this template**). The
**approval relay** (the human-in-the-loop daemon) is likewise a **companion
component not shipped here** — adopters bring or build their own (pattern
documented in `docs/human-in-the-loop.md`). Bootstrap symlinks the identity
files; you wire the remaining pieces once you have them.

## Adopting it

| Document | What it covers |
|---|---|
| [ONBOARDING.md](ONBOARDING.md) | Agent-facing walkthrough — read this before acting |
| [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md) | Seven-diagram architecture reference |
| [docs/memory-architecture.md](docs/memory-architecture.md) | The three durable memory layers + the always-on working-memory layer — and when to use each |
| [docs/wiki-protocol.md](docs/wiki-protocol.md) | Wiki traversal protocol — summary-first graph walk |
| [docs/permissions-protocol.md](docs/permissions-protocol.md) | Permission pipeline and human-in-the-loop detail |
| [docs/human-in-the-loop.md](docs/human-in-the-loop.md) | Relay setup guide |
| [docs/hygiene.md](docs/hygiene.md) | Session hygiene rules — what to capture, what to skip |
| [docs/multi-runtime.md](docs/multi-runtime.md) | Cross-runtime coordination patterns |
| [docs/executor-tier.md](docs/executor-tier.md) | Local-model executor tier — decision-free grunt-work layer beneath the agents |
| [config-templates/](config-templates/) | Starter configs for each runtime |
| [permissions/](permissions/) | Per-runtime permission rule files |
| [wiki-template/](wiki-template/) | SCHEMA.md + scaffold scripts for a new vault |
| [identity/](identity/) | Identity files — fill in `# Who I am` for your fleet |

Start at **ONBOARDING.md**. It routes you to the right section based on which
runtime you are running.

## License

MIT — see [LICENSE](LICENSE).
