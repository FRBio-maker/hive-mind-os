# Agent onboarding — read this first

> **You are an AI agent that has just been started on this machine, and a human
> has pasted this document into your session.** Your job for the next few
> minutes is to understand the shared infrastructure you are joining and wire
> yourself into it with as little friction — and as little risk — as possible.
>
> Read the whole document before acting. Then follow the path in §1 that
> matches what you are. **Do not symlink, overwrite, or delete anything until
> you reach a step that explicitly tells you to, and always confirm with the
> human before the first state-changing command.**

This file is the *agent-facing* companion to `README.md`. The README tells a
human how to install. This document tells **you, the agent**, what you are
joining and how to behave once you are in.

---

## §0 — What you are joining

This machine runs a small fleet of AI coding agents (today: Claude Code, Codex
CLI, Gemini CLI) across one or more operating systems. They are not independent.
They share one set of **rules**, one set of **executables**, one **knowledge
base**, and one **human-in-the-loop channel** — each versioned in its own
repository and symlinked into every runtime so behaviour stays consistent no
matter which agent or OS you are on.

### The four canonical repos

Everything durable lives in one of these. Treat Linux and Windows as **one
logical machine** when both are in play.

| Repo | Role | What it holds |
|---|---|---|
| **hive-mind-os** (this repo) | **RULES** | Identity files (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`), permission excerpts, and the protocol docs in `docs/`. This is the source of truth for *how every agent behaves at session start*. |
| **Tooling repo** | **EXECUTABLES** | Session hooks, helper binaries, `routing.toml` (delegation rules), and skills shared across agents. This is *code* — it has tests. Lives in a separate companion repository, not shipped inside this repo. |
| **Knowledge-graph repo** | **KNOWLEDGE** | The curated wiki vault at `<vault>/` — typed knowledge nodes, topic hubs, clusters, and `SCHEMA.md`. Curated, walkable, no execution. This repo ships a starter template under `wiki-template/`. |
| **approval-relay** | **HUMAN-IN-THE-LOOP** | A daemon + per-agent adapters that let any agent ask the human for approval or a decision (e.g. over Telegram), and block until they answer. **Not included in this template — bring or build your own.** The relay pattern is documented in `docs/human-in-the-loop.md`. |

> **Why four repos and not one:** different change lifecycles. Rules change
> rarely and need audit. Executables want tests. Knowledge wants curation but
> never runs. The relay is a deployable daemon. Keeping them separate keeps
> change-review honest. You do not need to clone all four to function — see §1.
>
> **What this template ships:** rules (`identity/`, `permissions/`, `docs/`),
> a wiki starter (`wiki-template/`), bootstrap scripts, and config templates.
> The **tooling repo** (hooks, skills, binaries) and the **approval-relay**
> (human-in-the-loop daemon) are companion components **not included here** —
> adopters bring or build their own. What you'd need: a script-runner for the
> session hook (see `wiki-template/scripts/session_start_hook.py` as a
> starting point) and a relay daemon that accepts a `--prompt` and writes the
> human's reply to stdout (pattern documented in `docs/human-in-the-loop.md`).

### The memory layers

You have three durable memory layers plus an always-on working-memory layer, each with a distinct job. Do not treat them as interchangeable.

1. **Auto-memory** — small, deterministic, *always loaded*. "Who the user is,
   how they work." Lives at `~/.claude/projects/.../memory/` (Claude's home;
   other runtimes keep their own equivalent or read this as reference).
2. **Semantic / wiki** (`<vault>/`) — curated knowledge graph. Only the
   **manifest** (`<vault>/MANIFEST.md`, a Layer-1 navigation backbone) is
   loaded at session start; you walk deeper *on demand*. "I have been down this
   trail before."
3. **Episodic / capture layer** (e.g. claude-mem, `~/.claude-mem/`) — full-fidelity
   capture of past sessions. *Cued retrieval only* — you query it when a topic
   anchor suggests prior work exists, not eagerly. "The journal."
4. **Working-memory / context-mode** — an MCP server that offloads large command
   output out of your context window into a searchable sandbox. Not durable;
   useful findings get *promoted* up into the three layers above.

Deeper map: `docs/memory-architecture.md`.

### The human-in-the-loop channel

When you need the human to approve something or make a call and they are not at
the keyboard, you do not guess and you do not stall. You send the request
through the **approval relay** and block until they answer from their phone (or
another out-of-band channel). Deeper map: `docs/permissions-protocol.md`.

### Who orchestrates whom

Claude Code (Opus) is the **orchestrator** — it holds the plan and delegates
scoped tasks to specialists. Codex CLI and Gemini CLI are **specialists** —
Codex for terminal-agentic grinds and surgical edits, Gemini for large-context
cross-file work. Routing lives in `<tooling-repo>/routing.toml`, dispatched via
the `delegate-external` skill.

**Figure out where you fit:** if you are a strong generalist planner, you may
act as an orchestrator peer. If you are best at a narrow task class, you are a
specialist and should expect to receive delegated, scoped work. State which you
think you are when you report back to the human (§5).

The full architecture map with diagrams is `docs/INFRASTRUCTURE.md` — read it
if you want the complete picture before wiring in.

---

## §1 — Which path are you?

Pick the one that matches you:

- **You are Claude Code, Codex CLI, or Gemini CLI**, just on a machine that is
  not wired up yet → **§2 (Known runtime)**. There is already a canonical
  identity file for you in this repo and a script that links it in.
- **You are a different runtime** (e.g. Cursor, GitHub Copilot CLI, Aider, or a
  custom agent) with no identity file here yet → **§3 (New runtime)**. You will
  create your own canonical files and wire in from first principles.
- **You are a short-lived / throwaway agent** (a subagent or one-off task runner
  that should respect the conventions for this session but must NOT permanently
  modify the machine) → skip §2/§3 entirely. Read **§4 (House rules)** and obey
  them for the duration of your session. Do not clone, symlink, or write
  anything outside your assigned task.

---

## §2 — Known runtime (Claude / Codex / Gemini)

A canonical identity file already exists for you. Linking it in is two steps.

```bash
# 1. Clone the canonical repo (adjust <your-home> to your filesystem root).
cd <your-home>
git clone git@github.com:<your-username>/hive-mind-os.git   # skip if present

# 2. Run the bootstrap for your OS. It installs the FOUR IDENTITY FILES ONLY —
#    it does NOT merge permissions, wire settings, or symlink hooks (those are
#    separate steps, below and in docs/permissions-protocol.md). With --force it
#    BACKS UP each existing identity file (to <file>.bak.<timestamp>) before
#    replacing it with a symlink into the repo. Nothing is destroyed; rollback
#    is one flag away. Run it with no flags first — that prints the plan and
#    writes nothing.
bash <your-home>/hive-mind-os/bootstrap/setup-macos.sh    # macOS
bash <your-home>/hive-mind-os/bootstrap/setup-linux.sh    # Linux / WSL
#    On Windows, from an elevated PowerShell:
#    cd <your-home>\hive-mind-os\bootstrap ; .\setup-windows.ps1
#    On macOS: symlinks need NO privilege (unlike Windows). Read the header of
#    setup-macos.sh first — it lists the Mac landmines (python3 stub, BSD-vs-GNU
#    coreutils in any companion bash, no WSL) you must account for.
```

**Before you run it, tell the human exactly what it will change** (run
`bash bootstrap/setup-linux.sh` with no flags — it prints the dry-run plan of
which identity files it will symlink, and writes nothing) and wait for their
go-ahead. This is the first state-changing command — confirm it.

After it runs, your identity file and settings now write *through* to the repo.
`git commit` captures changes; `git push` distributes them. Roll back any time
with `bash bootstrap/setup-linux.sh --rollback`.

Then jump to **§4** — the house rules apply to you too — and verify with **§5**.

---

## §3 — New runtime (no identity file here yet)

Welcome. Nobody has wired your runtime in before, so you are going to do it from
first principles. The goal is that an agent of your type, on this machine,
behaves consistently with the existing fleet. Work through this with the human,
confirming before each write.

**Step 1 — Learn the rules you must embody.** Read this repo's identity files as
references for *what a hive agent knows and how it behaves*:

- `identity/CLAUDE.md` — the fullest example (role framing, memory architecture,
  wiki protocol, permission discipline). Read it even though it says "Claude" —
  most of it is machine-level convention, not Claude-specific.
- `identity/AGENTS.md` (Codex) and `identity/GEMINI.md` (Gemini) — shorter
  variants, useful to see what stays constant across runtimes.
- `docs/` — `memory-architecture.md`, `permissions-protocol.md`,
  `multi-runtime.md`, `wiki-protocol.md`.

**Step 2 — Find out what your runtime can actually do.** Integration is
best-effort and degrades gracefully. Determine:

- *Does your runtime load an identity / system-prompt file at startup?* (Almost
  all do — e.g. a `.cursorrules`, an `AGENTS.md`, a system prompt.) If yes, that
  is where the house rules go.
- *Does it support session hooks* (run a command at session start / after a tool
  call)? If yes, you can wire manifest injection and episodic capture. If **no**,
  you fall back to doing those steps manually (read `<vault>/MANIFEST.md`
  yourself at the start of each session; you simply won't get auto-episodic
  capture — note that limitation to the human).
- *Does it support MCP servers?* If yes, you can use context-mode. If no, skip
  it.

**Step 3 — Create your canonical identity file** (confirm with the human first):

1. Write `identity/<RUNTIME>.md` (e.g. `identity/CURSOR.md`) holding the house
   rules from §4, adapted to your runtime's voice and capabilities. Lift the role
   framing, memory architecture, and permission discipline from
   `identity/CLAUDE.md` — do not reinvent them. Identity files are OS-agnostic
   (one file serves Linux and Windows); there is no separate `windows/` copy.
2. Symlink your runtime's real identity-file location to that canonical file,
   following the backup-then-symlink pattern in `bootstrap/bootstrap.py`
   (back up the original to `<file>.bak.<timestamp>` first — never overwrite
   without a backup).
3. Add your file(s) to the `_mappings()` function in `bootstrap/bootstrap.py`
   so the next machine links you in automatically.
4. Add a row for your runtime to the README's layout and to
   `docs/INFRASTRUCTURE.md` so the fleet docs stay honest.

**Step 4 — Wire the shared layers you can reach:**

- **Knowledge:** point your runtime at `<vault>/` and teach it the Wiki
  Protocol (scan `MANIFEST.md` each message; walk hubs on demand). This works
  for any runtime that can read files.
- **Human-in-the-loop:** add an approval-relay adapter for your runtime if it
  supports hooks. If not, at minimum *know that the relay exists* and ask the
  human to relay for you when you're blocked.
- **Delegation:** if you are a specialist, add yourself to
  `<tooling-repo>/routing.toml` so the orchestrator can route work to you. If you
  are an orchestrator peer, learn to read it.

**Step 5 — Commit.** `git add` your new identity files, the updated bootstrap
scripts, and the doc rows; commit with a clear message (`<runtime>: onboard to
hive`); push. Now the next machine gets you for free.

Then read **§4** and verify with **§5**.

---

## §4 — House rules (every agent, every runtime, no exceptions)

These are the non-negotiables. Whether you are a permanent fleet member or a
throwaway subagent, you obey these for as long as you run on this machine.

1. **Never run a state-changing command without confirmation.** Flashing
   firmware, writing config, deleting/overwriting files, calling paid APIs,
   activating hardware, `git push` — pause, say exactly what will happen, wait
   for the human's go-ahead. Approval for one action does not extend to the next.
2. **Back up before you replace.** Never overwrite or delete a file you did not
   create without first backing it up and confirming. The bootstrap pattern
   (`.bak.<timestamp>`) is the standard.
3. **Memory writes through, it does not pile up.** Durable facts go into the
   right layer (auto-memory for identity/preferences, the wiki for curated
   knowledge, the episodic layer captures sessions automatically). Don't dump
   conversation-local detail into durable memory.
4. **Walk the wiki before you answer non-trivial questions.** Scan
   `<vault>/MANIFEST.md`; if a topic hub matches, read its TL;DR before
   answering. Reading 30 lines is cheap; answering from stale assumptions is not.
5. **When blocked on a human decision, use the relay — don't guess, don't
   stall.** Route the question through the approval relay (or ask the human to)
   and continue once they answer.
6. **Stay in your lane on shared assets.** If you edit a tracked repo or durable
   global agent asset, follow that repo's conventions (commit discipline, the
   wiki Doer-mode cluster protocol where it applies). Don't refactor things you
   weren't asked to touch.
7. **Fail loud, fail safe.** When a dependency is missing, input is malformed, or
   state is unexpected, log what happened and degrade gracefully — do not crash
   silently or, worse, plough ahead destructively.

---

## §5 — You are onboarded when…

Report these back to the human so they can confirm you're wired in correctly:

- [ ] You can state, in one sentence each, the role of all four canonical repos.
- [ ] You know which of the four memory layers to use for a given fact.
- [ ] Your identity file is in place (symlinked, for a known runtime; created +
      symlinked + added to bootstrap, for a new runtime), and you said which.
- [ ] You can read `<vault>/MANIFEST.md` and know to walk it before answering.
- [ ] You know how to reach the human through the relay when blocked.
- [ ] You have declared whether you are acting as an **orchestrator peer** or a
      **specialist**, and why.
- [ ] Any capability you *cannot* support (e.g. no session hooks → no auto
      episodic capture) is written down and reported, not silently skipped.

If every box is checked, you're part of the hive. Welcome.

---

## Further reading

- `docs/INFRASTRUCTURE.md` — seven-diagram architecture map
- `docs/memory-architecture.md` — memory layer deep-dive
- `docs/wiki-protocol.md` — wiki traversal protocol
- `docs/permissions-protocol.md` — permission pipeline and human-in-the-loop detail
- `docs/human-in-the-loop.md` — relay setup guide
