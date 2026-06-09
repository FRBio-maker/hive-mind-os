# Multi-Runtime Parity

How one doctrine drives four agent runtimes from a single set of principles.

The Wiki Protocol, memory rules, permissions logic, and hygiene conventions are
runtime-agnostic. But each runtime reads its configuration from a different file
format and path. This document covers how to replicate the shared doctrine across
all four, and where the runtimes diverge.

---

## Where each runtime reads its config

| Runtime | Identity / doctrine file | Settings / config file | Format |
|---|---|---|---|
| Claude Code | `~/.claude/CLAUDE.md` | `~/.claude/settings.json` | JSON |
| Codex CLI | `~/.codex/AGENTS.md` | `~/.codex/config.toml` | TOML |
| Gemini CLI | `~/.gemini/GEMINI.md` | `~/.gemini/settings.json` | JSON |
| Grok | *(reads `AGENTS.md`)* | — | — |

Each runtime's identity file is the equivalent of this repo's `ONBOARDING.md`
plus the shared protocol text — translated into whatever that runtime expects.

---

## The duplication tradeoff

The shared protocol text — the Wiki Protocol, memory-layer rules, routing
logic — is **pasted into each runtime's identity file** as a local copy. There
is no central file that all runtimes import at runtime; each keeps its own.

**Why not centralize?**

- Runtime identity files are machine-local config, not version-controlled source.
  They live in `~/.claude/`, `~/.codex/`, etc. — different tools, different
  readers, no shared import mechanism.
- Each runtime has its own file format and frontmatter conventions. A single
  canonical source would require a build step to fan out to four targets.
- Portability wins over DRY here: any runtime works standalone, with no
  dependency on the others being present.

**The cost:** when you update a shared rule (e.g. the Wiki Protocol gains a new
walk constraint), you must update it in all four identity files. A simple diff
or grep across the four files catches drift. For a small number of runtimes this
is tolerable; at larger scale, a fan-out generation step becomes worthwhile.

---

## Codex CLI on WSL — specifics

Codex runs inside WSL (Windows Subsystem for Linux) and has a few config knobs
that matter for agent use.

### Exec permission approvals

```toml
exec_permission_approvals = true
```

Set this in `~/.codex/config.toml`. Without it, Codex will not prompt for
approval before executing shell commands — it will either auto-run or auto-block
depending on defaults. Enabling it surfaces the permissions hook so the
human-in-the-loop relay (or a terminal prompt) can intercept risky commands.

### Per-project trust

Codex uses a project trust level to decide how much latitude to give itself
inside a directory. Grant trust explicitly per project:

```toml
[projects.'<your-project-path>']
trust_level = "trusted"
```

Substitute your own absolute path. Adopters add one `[projects.*]` stanza per
project they want to grant. Without a trust entry, Codex applies a more
conservative default that will generate more permission prompts for routine
operations inside the project.

---

## The `$()` subexpression caveat

Commands containing a shell subexpression — `$()` — **always trigger a
permission prompt**, regardless of the allow-list. This is a hardcoded safety
gate in the runtime, not a bug. The allow-list cannot override it.

In practice: avoid wrapping commands in cosmetic `$()` when writing
agent-run instructions or hook scripts. A command like:

```bash
echo $(git rev-parse HEAD)
```

will prompt even if `echo` and `git` are both on the allow-list, because the
shell subexpression triggers the gate before the allow-list check runs.

Rewrite to avoid the subexpression when possible:

```bash
git rev-parse HEAD
```

This applies to all four runtimes to varying degrees, but is most consistently
enforced in Codex CLI. When debugging unexpected permission prompts, check
for `$()` in the flagged command first.

---

## Routing between runtimes

The doctrine does not require all four runtimes to be active simultaneously.
A minimal setup runs Claude Code only and ignores the rest. The value of
multi-runtime parity is that you can route tasks to the best-fit runtime without
retraining each one on your conventions:

- **Claude Code** — judgment-heavy tasks, orchestration, wiki maintenance,
  anything requiring nuanced planning.
- **Codex CLI** — terminal-agentic grinds, surgical edits, iteration-speed
  tasks inside a single repo.
- **Gemini CLI** — large-context cross-file work where holding the whole
  codebase in view at once matters.
- **Grok** — live web research and current-information lookups (its built-in
  web search is a real edge over the other three), plus best-of-N parallel
  attempts where trying a problem several ways beats one careful pass.

When all four share the same protocol text, a task handed from one to another
does not require a re-briefing. The receiving runtime already knows the wiki
conventions, memory rules, and escalation paths.
