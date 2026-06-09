# Start here

*A one-page orientation. Doctrine as of 2026-06-09.*

**What this is:** a portable *operating doctrine* that makes several independent
AI coding agents (Claude Code, Codex CLI, Gemini CLI, Grok) behave like one
supervised team — sharing one knowledge graph, one permission model, and one set
of house rules. It is **not** a running system you install; it is the rulebook,
templates, and installer for one. The intelligence is in *shared conditioning and
shared retrieval*, not agent-to-agent magic.

---

## What you get vs. what you wire

The doctrine separates four concerns. **This repo ships two of them**; the other
two are companions you bring or build (their *contracts* are documented so you can
use whatever you already run).

| Concern | In this repo? | What it is |
|---|---|---|
| **RULES** | ✅ shipped | `identity/` (per-agent doctrine files), `permissions/` (deny/ask/allow excerpts), `docs/` (the protocols), `config-templates/` |
| **KNOWLEDGE (starter)** | ✅ shipped | `wiki-template/` — schema + scaffold + manifest generator + binding lint |
| **INSTALL** | ✅ shipped | `bootstrap/` — symlinks identity files in, with backup + rollback |
| **EXECUTABLES** | 🔌 you wire | session hooks, delegation routing, shared skills — a separate tooling repo |
| **HUMAN-IN-THE-LOOP** | 🔌 you wire | the approval-relay daemon (phone approvals) — pattern in `docs/human-in-the-loop.md` |
| **EPISODIC + WORKING memory** | 🔌 you wire | an episodic capture tool (e.g. claude-mem) + a context-offload MCP (e.g. context-mode) |
| **EXECUTOR tier** | 🔌 you wire | a local GGUF model server for cheap grunt work — pattern in `docs/executor-tier.md` |

**The seams are contracts, not imports.** Each companion meets a one-line contract:
the session hook needs a script-runner (`wiki-template/scripts/session_start_hook.py`
is the reference); the relay needs a command that takes `--prompt` and writes the
human's reply to stdout; the executor needs any OpenAI-compatible local endpoint.
Meet the contract with whatever you already have.

---

## The fastest path to value

You do **not** need all four companions to start. Minimum viable adoption:

1. **Install the rules.** `bash bootstrap/setup-linux.sh` (dry-run first; `--apply`
   when happy). This symlinks the identity files into your agent runtimes — your
   agents now share the same house rules. *Works day one.*
2. **Scaffold a vault.** `python3 wiki-template/scripts/scaffold.py --vault <path>`.
   You now have a knowledge graph + the manifest the agents walk.
3. **Merge the permissions.** Hand-merge `permissions/` excerpts into each agent's
   live settings (they carry the hard-denies + ask rules). See `permissions/README.md`.

That's a coherent, useful system. The companions (hooks for auto-injection, the
phone relay, episodic capture, a local model) are **incremental** — add them as you
need them, each behind a documented contract.

---

## Where to go next

| You are… | Read |
|---|---|
| A human installing it | [`README.md`](README.md) → [`docs/REPO-MAP.md`](docs/REPO-MAP.md) |
| An AI agent being onboarded | [`ONBOARDING.md`](ONBOARDING.md) (paste it into the agent) |
| Wanting the full architecture | [`docs/INFRASTRUCTURE.md`](docs/INFRASTRUCTURE.md) (7 diagrams) |
| Tuning permissions / the relay | [`docs/permissions-protocol.md`](docs/permissions-protocol.md), [`docs/human-in-the-loop.md`](docs/human-in-the-loop.md) |

**Honest expectation:** what you receive here is the rulebook and scaffolding, not
a turnkey clone of someone's running rig. If you can run an agent CLI, you can have
the doctrine + a live wiki working same-day; wiring the companions is a
multi-session project you do at your own pace.
