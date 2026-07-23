# The dashboard — the UI of the hive OS

A hive-mind OS is a fleet of daemons, hooks, watchdogs, schedulers, and memory
layers — and every one of them **fails silently by default**. A model tier's
watchdog relaunches it with the wrong profile; a capture hook dies and stops
writing; a Windows copy of a canonical file drifts; an overnight job never had
its trigger registered. None of these throw an error in front of you. The
motivating incident for this doc: a whole memory layer ran **broken for 10
days before anyone noticed** (see `docs/memory-architecture.md`, "the retired
third layer").

The dashboard started life as observability — a way to catch those silent
failures. It has since grown into something more: **the UI of the hive OS
itself.** One local, zero-cloud page (`127.0.0.1`) is where you *see* every OS
layer and where the OS's agent-agnostic capabilities — the job runner,
autonomous-run orchestration, checkpointing, relay presence — surface and get
controlled. Like the approval relay and the tooling repo, it is a **companion
component you wire** (🔌): this doc ships the pattern and the contracts, not
the code, because the collectors are necessarily coupled to *your* stores.

---

## The architecture pattern

Three constraints shape the whole design, and each exists for a reliability
reason:

**1. Collector-per-source, and a collector NEVER raises.**
The server is a thin shell over one small collector module per data source
(executor-tier proxy, session logs, delegation telemetry, job runner, vault,
...). The contract: a collector catches everything and returns a degraded
payload on failure. **A bad source degrades its own panel — it must never take
down the page.** This is the property that makes the dashboard trustworthy:
the cockpit stays up precisely when things are breaking, which is when you
need it.

This is also **how new agents join the OS**: a new runtime doesn't build its
own UI — it adds one collector module for its own state and appears as a panel
alongside everyone else. The dashboard is agent-agnostic by construction.

**2. Stdlib-only server, single self-contained frontend file.**
No framework, no build step, no CDN. One `server.py` on the standard library;
one `index.html` with inline CSS/JS that builds its shell once and refills
panels from a short poll (`/api/state`, ~2s). The OS's own UI must have
near-zero failure modes of its own — a dashboard that needs `npm install` to
diagnose your system adds a dependency chain exactly where you want none.
Zero-cloud also means it works offline and leaks nothing.

**3. Read-only by default; write actions are explicit, gated verbs.**
Collectors read logs, databases (read-only mode), and status endpoints — the
dashboard displaying a subsystem must not be able to corrupt it. The control
verbs (below) are a separate, visibly distinct path with their own gates.

---

## What to surface — one panel per OS layer

The panel list *is* an inventory of your OS's failure modes. The reference
implementation surfaces:

| Panel | Watches | The silent failure it catches |
|---|---|---|
| **Executor tier** | the proxy in front of the hosted cheap-model API: request pacing, daily-quota burn, per-consumer attribution | one consumer silently eating the day's quota; the proxy down while jobs queue |
| **Cloud agents** | per-agent 7-day token totals + live context-used bars from session logs | a runaway session burning context or spend |
| **Delegations** | the exec/outcome telemetry feed (see `docs/multi-runtime.md`) | dispatched work that never reported back |
| **Jobs** | the overnight job runner + its schedule | jobs enabled in config but **never actually registered** with the OS scheduler |
| **Autonomous runs** | live state of any unsupervised run: work packages, review-gate verdicts, branch, worker dispatches | an overnight run stalled or looping with no one watching |
| **Projects** | per-project status rendered from wiki **topic hubs** + spec/plan docs | the wiki drifting from reality (the hub *is* the truth — so show it) |
| **Wiki graph health** | binding queue, unbound clusters, promotion candidates | knowledge captured but never filed (orphan rot) |
| **Computer use** | OS-level GUI-agent sessions, with **attested** sandbox status | an agent driving the real host while claiming to be in a VM |

Two design rules from the panel list:

- **The scheduler owns time; the runner owns execution.** Don't let a
  long-lived daemon keep its own clock — register jobs with the OS scheduler
  (Task Scheduler / cron / launchd) and have it poke the runner. The dashboard
  then shows the *scheduler's* truth, not the daemon's intention. The gap
  between "job enabled in config" and "trigger actually registered" is a real
  failure class we hit twice.
- **Attest, don't trust.** For anything safety-relevant (is this GUI agent
  sandboxed?), the collector must cross-check the claimed state against
  independent evidence (a machine fingerprint) and **fail safe to red** —
  a missing or mismatched attestation counts as unsandboxed.

---

## The OS capabilities — what routes through this surface

Once every layer reports honestly, the same surface carries the OS's
**agent-agnostic capabilities** — the things any runtime in the fleet can use
without building its own machinery. Each is a gated verb, added one at a time:

### 1. The job runner (overnight / scheduled work)

A **jobs board**: each job is a real command with a schedule, rendered with
its scheduler-registration status (see the rule above). Two gates before a job
can run unattended:

- **Arming requires explicit human confirmation** — a job defined in config is
  *visible*, not *armed*. A human clicks/confirms the arm.
- **Arming requires a passing dry-run of the real command** — not a synthetic
  test: the actual command executes in dry-run mode and must succeed before
  the schedule goes live. "It would have worked" is proven, not assumed.

Job LLM calls go to the **executor tier** (`docs/executor-tier.md`) — overnight
volume is exactly what that tier is for, and it keeps unattended work off the
expensive, rate-limited agents.

### 2. Autonomous-run orchestration (the overnight "lone wolf" pattern)

Unsupervised multi-agent execution of a specced goal, structured so that no
human is needed until morning — and no damage is possible before then:

- One **CEO session** owns the goal and spawns **scoped orchestrators**, each
  bounded to a work package it can finish within its context budget.
- Orchestrators **dispatch workers per the routing table** (the same
  `routing.toml` the daytime fleet uses — no special overnight roster).
- **Review gates per work package**: each package passes verification and
  review before the next builds on it — failures defer-and-log rather than
  block or guess.
- All work lands on an **isolated branch that is never auto-merged**. Merging
  is a human decision, always.
- The run ends with a **morning report**: what shipped, what deferred, what
  needs a decision.

The dashboard's autonomous-runs panel is the live window into this — and the
kill switch.

### 3. Session checkpointing

The commands that flush session state into the durable memory layers
(`docs/memory-architecture.md`):

- **`/save`** — full checkpoint: finalize the wiki session cluster, write the
  handoff, commit.
- **`/quicksave`** — mid-session flush of working state into wiki nodes, no
  git machinery.

These are OS verbs, not one runtime's feature: any agent in the fleet
checkpoints the same way into the same vault, and the dashboard's wiki-health
panel shows whether checkpoints are actually landing.

### 4. Relay presence control

An **away-mode toggle** for the approval relay (`docs/human-in-the-loop.md`):
flip whether approval requests route to the phone (away) or the terminal
(present) from the same page that shows the relay's health. Presence is OS
state, so it lives in the OS's UI.

Keep the read path and the write path visibly separate. A control plane that
grew out of a read-only cockpit inherits its trust; one that started with
buttons doesn't.

---

## Wiring your own — the contract

- Any local HTTP server + one page; poll a single `/api/state` JSON endpoint.
- One collector module per source, each meeting the never-raise contract and
  returning `{ok, data, error}`-shaped payloads.
- Read your own stores: session logs, proxy JSONL, job-runner state file,
  vault scripts' JSON output, scheduler queries.
- New agent in the fleet? It joins by **adding a collector**, not a UI.
- Add a panel the day a subsystem bites you silently. The dashboard is an
  accumulating map of past silent failures — that's what makes it valuable.

## Cross-references

- `docs/memory-architecture.md` — the audit that motivates this layer, and the
  checkpoint workflow surfaced here.
- `docs/executor-tier.md` — the hosted cheap-model tier the executor panel
  watches and the job runner calls.
- `docs/multi-runtime.md` — the delegation telemetry the delegations panel
  renders, and the routing table autonomous runs dispatch through.
- `docs/human-in-the-loop.md` — the relay whose presence mode this surface
  toggles.
- `docs/hygiene.md` — the binding queue the wiki-health panel surfaces.
