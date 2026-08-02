---
name: browser-ops
description: >-
  Drive a REAL browser from the terminal to (A) test/QA a UI like a human and
  report bugs, (B) automate repeatable web tasks / RPA — log in, navigate,
  extract, submit, download — with persistent auth, or (C) attach to an
  already-running browser or a Chromium-based desktop app (Electron) via CDP.
  Fleet-wide capability usable by any runtime in the fleet. Use whenever a task
  needs to actually operate a web page/app, not just read code about one.
---

<!--
TEMPLATE NOTE — localize before use:
- PREREQUISITE (not vendored here): `playwright-cli`, Microsoft's
  terminal-driven Playwright CLI. Install it globally per its upstream docs
  and confirm `playwright-cli --help` works. All command mechanics live
  upstream; this skill is only the fleet-policy layer on top.
- Adjust the delegation-fit paragraph to your own routing.toml roster.
-->

# browser-ops — fleet browser & web automation

**What this is.** A thin fleet-policy layer over `playwright-cli` (external
prerequisite — see the template note). The **mechanics** (every command, task
guides for mocking / tracing / test-gen) live in the upstream tool's help and
docs. **This** skill adds: when to reach for it, the three operating modes, the
house bug-report format, the safety gate, session/artifact hygiene, and the
recipe for delegating a browser task to an external worker.

**Why it exists.** It gives the fleet actual *hands and eyes*: an agent can
drive a page by its accessibility tree (element refs `e1`, `e2`…), not by
guessing at screenshots. That catches runtime bugs static review can't, and
automates web work a human would otherwise do by hand.

---

## The core loop (memorize this)

```
snapshot  ->  act by ref  ->  re-snapshot  ->  verify state
```

1. `playwright-cli open <url>` (or `goto` if already open).
2. `playwright-cli snapshot` — returns the a11y tree with `[ref=eN]` handles
   AND a console error/warning count. Refs are how you target elements.
3. Act on refs: `click e5`, `fill e8 "text" --submit`, `select e9 val`, etc.
4. `snapshot` again to confirm the page changed as expected.
5. `close` when done (or `detach` to leave the browser running).

Snapshot is truth. Never act on a ref from a stale snapshot — the page may have
re-rendered and renumbered refs.

---

## Three modes

### Mode A — QA / bug-hunt (test the UI like a human)
Exercise a specific flow and report what breaks. The tool hands you the two
richest bug signals for free on every `snapshot`:
- **Console errors/warnings** (the `Console: N errors` line + the logged file).
- **Broken state** (expected element missing / wrong text after an action).
Also pull **network failures** and run assertions via `eval`:
```bash
playwright-cli eval "document.querySelector('.error')?.textContent"
playwright-cli eval "() => performance.getEntriesByType('resource').filter(r=>r.responseStatus>=400).length"
```
Report findings in the **house format** (below).

### Mode B — web ops / RPA (automate a repeatable web task)
Log in, navigate, extract data, fill/submit forms, upload/download files —
the stuff a human does at a desk. The key to *repeatability* is **persistent
auth** so you don't log in every run:
```bash
# one-time: log in interactively (headed), then save the authenticated state
playwright-cli state-save auth.json
# every run after: restore the session, skip the login
playwright-cli state-load auth.json
```
`state-*.json` holds cookies + localStorage = **live credentials**. Treat it as
a secret (see Safety). Extraction uses `eval` (run JS in the page) or
`snapshot`; downloads land where the browser is configured; `upload <file>` /
`drop` push files in.

### Mode C — attach (drive an existing browser or a desktop app)
Playwright speaks CDP (Chrome DevTools Protocol), so it can drive **any
Chromium-based target**, including **Electron desktop apps** (e.g. VS Code,
Slack, Discord) — not just pages it launched.
```bash
# attach to a browser/app already exposing a CDP endpoint
playwright-cli attach <name>          # attach to a running playwright browser
# (for a real Chrome/Electron app: launch it with --remote-debugging-port=9222,
#  then connect via the CDP endpoint — see the upstream session docs)
playwright-cli detach                 # leave it running when done
```
This is the one real bridge to "desktop" automation — see the boundary note.

---

## House bug-report format (Mode A output)

Return findings as a list. One block per bug, most-severe first:

```
### BUG: <one-line summary>
- Severity: blocker | major | minor
- Where: <url> — <element/flow>
- Steps: 1) … 2) … 3) …
- Expected: <what should happen>
- Actual: <what happened> (console: <error text if any>; network: <failed req if any>)
- Ref/evidence: <snapshot file, screenshot path, or console log line>
```
No bugs found → say so explicitly and list what flows you exercised, so "clean"
means "covered," not "didn't look."

---

## Safety gate (READ — this drives a REAL browser with REAL logins)

The fleet can be logged into email, banking, dashboards. A wrong click sends,
deletes, or pays for real. So:

1. **Confirm before outbound/destructive web actions** — sending a message,
   submitting a payment, deleting data, posting publicly. Same rule as any
   state-changing command: state what will happen, wait for the user. Read-only
   navigation / snapshot / extraction needs no confirmation.
2. **`state-*.json` is a secret.** Store it OUTSIDE any git repo (e.g.
   `~/.browser-ops/state/`), never commit it. It's a live session token.
3. **Headless by default for automation**, headed only when the user is
   watching or doing a one-time interactive login.
4. **Always snapshot before acting** so you target the right element, and read
   the console line every snapshot — surface errors even when the task
   "worked."
5. **Prefer a fresh session for untrusted sites**; don't load your authed
   state into a page you don't trust (it can read those cookies via the DOM).

---

## Session & artifact hygiene

- **Named sessions** let parallel tasks not collide:
  `playwright-cli -s=job1 open …` / `-s=job2 open …`. Each is an isolated
  browser.
- **Always `close`** (or `detach`) when done — orphaned browsers leak memory.
- **Artifacts land in `.playwright-cli/`** in the cwd (snapshots, console
  logs). Add `/.playwright-cli/` to the repo's `.gitignore` before running in
  a project so agents don't commit them. Same for any `state-*.json` and
  `auth.json`.

---

## Delegating a browser task to an external worker

The binary is on PATH for the whole fleet, and the upstream tool supports
**skills-less operation** — a worker can read the command surface off `--help`
itself. So do NOT copy this skill into each worker's config directory. Hand
the worker a brief (per `skills/delegate-external/`) that says what to drive
and points it at the CLI:

```
Goal: <exercise/automate X on <url>>.
Tool: playwright-cli is installed globally. Run `playwright-cli --help` for the
      command surface, then use the snapshot -> act-by-ref -> re-snapshot loop.
Deliverable: <bugs in the house format> | <extracted data as JSON> | <task done + evidence>.
Safety: read-only unless the goal says otherwise; confirm any outbound action.
```
Fit: terminal-agentic workers are the natural match for driving a CLI loop; the
orchestrator can also run it directly. Any roster worker that can shell out can
use the same binary — pick per your `routing.toml`.

---

## Boundary — browser ≠ full desktop (be honest about this)

`playwright-cli` drives **Chromium and Chromium-based (Electron) apps only**.
It CANNOT operate native OS apps, system dialogs, or move the mouse outside a
browser/Electron window. If a task needs true OS-level desktop automation
across arbitrary apps, that's a *different* tool (OS UI-automation frameworks
or a computer-use agent) — flag it as a separate capability, don't pretend
this covers it.

## See also
- Upstream `playwright-cli` docs + `playwright-cli --help` — full mechanics
- `skills/delegate-external/` — how to brief a worker
- `config-templates/hivemind/routing.toml` — which worker for which class
