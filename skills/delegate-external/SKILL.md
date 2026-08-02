---
name: delegate-external
description: >-
  Delegate a scoped task from the apex/orchestrator runtime to an external
  worker CLI from a different model family. Use when a task class better fits a
  non-apex runtime per your routing.toml — long terminal-agentic grinds,
  large-context cross-file edit work, live web research, best-of-N parallel
  attempts, answer-only expert consults, or cheap parallel cleanup. Skip when
  the task is small, requires orchestrator-level judgment, or fits the
  runtime's native subagent tool.
---

<!--
TEMPLATE NOTE — localize before use:
- The worker roster, model IDs, and verified invocation flags live in YOUR
  routing.toml (template: config-templates/hivemind/routing.toml). This skill
  deliberately names no specific CLI, model ID, or path: CLIs change flags and
  retire models faster than skill files get edited. The TOML is the single
  place you keep verified, current dispatch patterns.
- The shell examples below are POSIX-flavored pseudo-commands. On Windows,
  watch two classic hazards: (1) passing a multi-line brief as a quoted
  argument gets mangled — always pass briefs via a file or stdin; (2) legacy
  PowerShell decodes files with the ANSI code page by default, silently
  corrupting UTF-8 (em-dashes, arrows) before the worker ever sees them —
  force UTF-8 explicitly when piping a brief.
-->

# Delegate External

You (the orchestrator) hand a scoped task to an external agent CLI from a
different model family as a worker.

Three layers, kept separate on purpose:

- **This skill is the decision layer** — when to delegate, how to brief, how to
  verify.
- **The native CLI invocations are the execution layer** — exact commands per
  worker.
- **`routing.toml` is the data layer** — which worker for which task class,
  with the verified model IDs and flags for *your* machine. It is editable
  plaintext because per-model rankings shift faster than this skill. Read it
  before every dispatch.

---

## When to use this skill

**Use it when ALL of these hold:**

1. The task is **decomposable** — a worker can complete it from a
   self-contained brief with no follow-up clarifying questions to you.
2. The task class has a **cost or capability advantage** on another runtime per
   `routing.toml` (cheaper, faster, bigger context, or higher benchmark).
3. You can **verify the result** afterward (the worker produces files, output,
   or a diff you can read).

**Do NOT use it for:**

- Architecture or product decisions — never delegate judgment.
- Tasks under ~5 minutes of inline work — dispatch overhead exceeds savings.
- Anything where you'd need a back-and-forth with the worker mid-task —
  workers don't talk back; if you'd need iteration, do it yourself.
- Same-family subagent work — for that, use your runtime's native subagent
  tool. This skill is specifically for *external* (cross-vendor) CLIs.

---

## Decision flow

```
Task arrives
   │
   ├─ Is it judgment / architecture / product? ─── YES → do it yourself
   │   NO
   │
   ├─ Is it < 5 min of inline work?            ─── YES → do it yourself
   │   NO
   │
   ├─ Is the worker your own model family?     ─── YES → native subagent tool
   │   NO
   │
   ├─ Read routing.toml
   │  Find the entry matching task_class.
   │  If no clean match → do it yourself, then propose a new
   │  routing.toml entry to the user.
   │
   ├─ Build the brief (see Brief Format below).
   │
   ├─ Invoke natively (model + verified flags per routing.toml).
   │
   ├─ Read the worker's stdout + `git status`/`git diff` in the workdir.
   │
   └─ Review. If incomplete, decide: retry once with sharper brief,
      escalate to a stronger model, or take it over yourself.
```

## The six-step delegation procedure

Every dispatch, regardless of worker:

1. **Route** — read `routing.toml`, match the task class to a worker, take the
   model ID and flags from there (never from memory, never from this file).
2. **Brief** — write the brief to a file (format below). Self-contained; the
   worker won't ask follow-ups.
3. **Snapshot** — record git state in the workdir first (`git rev-parse HEAD`
   + `git status --porcelain`) so you can diff and revert cleanly.
4. **Dispatch** — run the worker non-interactively, brief via file or stdin,
   capped with a timeout. Keep read-only tasks read-only *by construction*
   (disallow edit/shell tools) rather than by trust.
5. **Inspect** — capture stdout, then diff the workdir (`git diff`,
   `git status --porcelain`) to get the actual changed files.
6. **Verify + log** — run the brief's `verification` command; accept, patch,
   retry, or take over. If your fleet keeps a delegation log, record the
   dispatch (worker, task class, exit code, duration) and later the outcome —
   measured in the same call as the dispatch, not eyeballed.

---

## Task class taxonomy (match these against routing.toml)

| Class | Signature |
|---|---|
| `terminal_agentic_grind` | multi-step CLI/bash work, build pipelines, debug loops, env setup |
| `surgical_code_edit` | scoped diff in a known file or two — refactor, rename, add a parameter |
| `cross_file_feature` | end-to-end feature touching 3+ files, may include tests |
| `long_context_grind` | read N files (often 20+), summarize, extract patterns, answer about whole codebase |
| `expert_consult` | long-context expert opinion / design critique, answer-only, no file edits |
| `web_research` | live web search, prior-art checks, best-of-N parallel attempts |
| `cheap_cleanup` | formatting, lint fixes, comment passes, doc string filling |
| `architecture_decision` | ⛔ never delegate — do it yourself |
| `second_opinion_review` | get a critique from a *different family* than the implementer |

When unsure, ask the user or default to `do it yourself`.

---

## Brief format

A brief is a markdown file with YAML frontmatter:

```markdown
---
task_class: surgical_code_edit
role: worker          # ALWAYS worker — see "Role is stated, not resolved" below
goal: "One sentence — what 'done' looks like in plain English."
workdir: /absolute/path/to/project
deliverable: "Concrete artifact spec — e.g. 'modified file X with function Y added'"
verification: "How the orchestrator will check — e.g. 'pytest tests/test_foo.py passes'"
constraints:
  - "Do NOT touch files outside src/"
  - "Match existing code style"
  - "No new dependencies"
allowed_tools: [read, edit, bash]
---

# Task

Full description. Be explicit about scope. The worker won't ask follow-up
questions — anything ambiguous becomes the worker's interpretation, which
is usually wrong.

## Context the worker needs

- Why this matters (1-2 sentences)
- Any prior decisions that shape this
- File paths the worker should read first
```

### Role is stated, not resolved

Always set `role: worker` in the frontmatter. **You are asserting a fact about
the subprocess, not looking one up.** Hivemind OS's `roles.toml` records which
agent *holds* a role; it says nothing about what a given *process* is. A worker
that resolves its own role from that file can self-assign an apex role — and
then start spawning work of its own inside what was meant to be one scoped
task. The dispatcher always knows the callee is a worker, so say so; never make
the callee rediscover the org chart.

Stating it in the brief also puts the role in the dispatch log, so a
misbehaving run shows what role the worker thought it had instead of leaving
you to guess.

**House rules are NOT in the brief** — they belong in each worker's identity
file (its equivalent of `AGENTS.md` / instructions file) per your fleet's
parity protocol. Don't duplicate. If you find yourself needing to repeat a
global preference, fix the identity file, not the brief.

---

## Dispatch mechanics (generic — verified specifics live in routing.toml)

- **Pass briefs via a file or stdin, never a quoted argument.** Multi-line
  briefs get mangled as argv tokens on most shells.
- **Read-only by construction.** For consults and reviews, disallow the
  worker's edit/write/shell tools where its CLI supports it; never reach for
  the CLI's "auto-approve everything" flag to make a dispatch go through.
- **Edit mode = git workspace + diff review.** Some CLIs have only an
  all-or-nothing headless approval knob. Always run edit-capable dispatches
  against a git workspace, then `git diff` and revert anything out-of-scope.
  Stdout is the worker's transcript; the real deliverable is the diff.
- **Judge success by the EXIT CODE, not stderr.** Shell wrappers routinely
  echo harmless status noise to stderr. Conversely, a bad model ID or a
  trusted-directory check can fail fast with exit 1 and *empty stdout* — which
  reads exactly like a silent worker if you only look at output. Check both
  exit code and stderr on failure.
- **Sandboxes may block git.** Some worker sandboxes cannot commit; the
  orchestrator commits from its own side after review.
- **Timeout every dispatch** so a stalled worker can't hang the run.

---

## After the worker returns

1. **Sanity check** — do the changed files match `deliverable`? If the worker
   touched files it shouldn't have, treat the result as suspect.
2. **Verify** — run the `verification` command from the brief. If it fails,
   either retry with a sharper brief or take over.
3. **Log** (optional but recommended) — exec + outcome as two correlated
   entries in your delegation log so routing statistics stay honest. A failed
   log write must never abort the delegation.

---

## Failure modes to watch for

- **Identity drift** — the worker violates house preferences: its identity
  file is out of sync with the orchestrator's. Surface it as a parity bug;
  don't patch around it in briefs.
- **Out-of-scope edits** — worker touched files outside the brief's
  `constraints`. Revert with `git checkout -- <file>` and retry with tighter
  constraints, or take it over.
- **Stale routing** — a worker repeatedly underperforms for its assigned
  class: propose a `routing.toml` edit. Don't just retry blindly.
- **Worker exit non-zero but files changed** — worker crashed mid-task. Don't
  trust the partial diff; revert and retry or take over.
- **Encoding corruption (Windows)** — a brief piped through a shell that
  decodes with the ANSI code page reaches the worker as mojibake, and the
  worker faithfully writes the garbage into your files. Force UTF-8; scan
  diffs that carried non-ASCII before accepting.

---

## See also

- `config-templates/hivemind/routing.toml` — the routing table template (your live copy is the data layer)
- `skills/consult/` — the cross-vendor decision consult built on this dispatch layer
- `docs/multi-runtime.md` — the fleet model this skill operates inside
