# Observability — the dashboard layer

A hive-mind OS is a fleet of daemons, hooks, watchdogs, schedulers, and memory
layers — and every one of them **fails silently by default**. A model server's
watchdog relaunches it with the wrong profile; a capture hook dies and stops
writing; a Windows copy of a canonical file drifts; an overnight job never had
its trigger registered. None of these throw an error in front of you. The
motivating incident for this doc: a whole memory layer ran **broken for 10
days before anyone noticed** (see `docs/memory-architecture.md`, "the retired
third layer"). Observability is how the OS earns the right to run unattended.

The reference implementation is a **fleet dashboard** — a local, zero-cloud
cockpit (one HTTP page on `127.0.0.1`) that renders the live state of every
OS layer. Like the approval relay and the tooling repo, it is a **companion
component you wire** (🔌): this doc ships the pattern and the contracts, not
the code, because the collectors are necessarily coupled to *your* stores.

---

## The architecture pattern

Three constraints shape the whole design, and each exists for a reliability
reason:

**1. Collector-per-source, and a collector NEVER raises.**
The server is a thin shell over one small collector module per data source
(model server, session logs, delegation telemetry, job runner, vault, ...).
The contract: a collector catches everything and returns a degraded payload
on failure. **A bad source degrades its own panel — it must never take down
the page.** This is the property that makes the dashboard trustworthy: the
cockpit stays up precisely when things are breaking, which is when you need
it.

**2. Stdlib-only server, single self-contained frontend file.**
No framework, no build step, no CDN. One `server.py` on the standard library;
one `index.html` with inline CSS/JS that builds its shell once and refills
panels from a short poll (`/api/state`, ~2s). The observability layer must
have near-zero failure modes of its own — a dashboard that needs `npm
install` to diagnose your system adds a dependency chain exactly where you
want none. Zero-cloud also means it works offline and leaks nothing.

**3. Read-only against the stores it observes.**
Collectors read logs, databases (read-only mode), and status endpoints. The
dashboard displaying a subsystem must not be able to corrupt it.

---

## What to surface — one panel per OS layer

The panel list *is* an inventory of your OS's failure modes. The reference
implementation surfaces:

| Panel | Watches | The silent failure it catches |
|---|---|---|
| **Local model** | executor-tier server profile (model / ctx / KV) | a watchdog relaunch silently downgrading the profile |
| **Consumers** | per-consumer token attribution via a logging proxy in front of the model | one consumer silently eating the local tier |
| **Cloud agents** | per-agent 7-day token totals + live context-used bars from session logs | a runaway session burning context or spend |
| **Delegations** | the exec/outcome telemetry feed (see `docs/multi-runtime.md`) | dispatched work that never reported back |
| **Jobs** | the overnight job runner + its schedule | jobs enabled in config but **never actually registered** with the OS scheduler |
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

## From cockpit to control plane

Observability is phase 1. Once every layer reports honestly, the same surface
grows write actions — carefully, one gated verb at a time:

- **Watchdogs + heartbeats** on the runner and the dashboard itself (who
  watches the watcher: a heartbeat file the other party checks).
- **Run-now / schedule editing** for jobs (writes go through the scheduler,
  per the rule above).
- **Mode toggles** — e.g. flipping the approval relay's AFK mode from the page.
- **Memory-health and injection-budget panels** — observability *of the memory
  doctrine itself*: how many tokens each session-start source injects, whether
  the checkpoint hook is firing, how stale each hub's truth block is.

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
- Add a panel the day a subsystem bites you silently. The dashboard is an
  accumulating map of past silent failures — that's what makes it valuable.

## Cross-references

- `docs/memory-architecture.md` — the audit that motivates this layer.
- `docs/executor-tier.md` — the local-model tier the model/consumer panels watch.
- `docs/multi-runtime.md` — the delegation telemetry the delegations panel renders.
- `docs/hygiene.md` — the binding queue the wiki-health panel surfaces.
