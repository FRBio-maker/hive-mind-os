# The role-slot control plane — CEO / orchestrator / worker

Hivemind OS does not hardcode "Claude orchestrates, everyone else specializes."
**Role is a slot an agent is assigned, not a fixed property of who the agent
is.** The human swaps agents in and out of the three roles through two tiny
files — the control plane — and each identity file tells its agent to resolve
its live role from them at session start.

The three playbooks in this folder are the operating manuals for each slot:

| Playbook | Slot | Apex when |
|---|---|---|
| [`CEO-PLAYBOOK.md`](CEO-PLAYBOOK.md) | CEO | `mode.state` = `away` (unsupervised / overnight) |
| [`ORCHESTRATOR-PLAYBOOK.md`](ORCHESTRATOR-PLAYBOOK.md) | orchestrator | `mode.state` = `present` (human-in-the-loop) |
| [`WORKER-PLAYBOOK.md`](WORKER-PLAYBOOK.md) | worker | never apex — one scoped task at a time |

Starter copies of the control-plane files ship at
[`config-templates/hivemind/`](../../config-templates/hivemind/):
`roles.toml` (who holds which slot, and the worker pool), `mode.state`
(`present` or `away`), and `routing.toml` (which worker gets which task class).

---

## The two control-plane files

**`roles.toml`** names which agent currently holds the CEO slot, which holds
the orchestrator slot, and the worker pool everyone else (including the
off-duty apex agents) belongs to. Note that **`flash` — the executor tier
(`docs/executor-tier.md`) — is a first-class member of the worker pool**, not
a footnote below it: routing can send decision-free volume work there like any
other worker.

**`mode.state`** is a one-word file: `present` or `away`.

- `present` → the **orchestrator** agent is the apex, with the human in the
  loop above it.
- `away` → the **CEO** agent is the apex, running unsupervised until the human
  returns.

An agent that holds an apex slot in the *wrong* mode is just a worker: the CEO
agent in `present` mode is a worker; the orchestrator agent in `away` mode is
a worker. Only one apex exists at a time.

> ⚠️ **Do not confuse `mode.state` "away" with the relay's presence (AFK)
> toggle.** The relay toggle (`docs/human-in-the-loop.md`) only decides whether
> approval prompts go to your phone or your terminal. `mode.state = away`
> changes *who is in charge*: it hands the apex to the CEO agent for
> unsupervised operation. Flipping it is a command decision, not a
> notification preference.

## Precedence: dispatched ⇒ worker. Full stop.

If another agent dispatched you with a scoped task, **you are a worker for
that run** — do not resolve your own role from `roles.toml`. That file records
which agent *holds* a role, not what *this process* is. A delegated run that
self-assigns an apex role will start spawning work of its own inside what was
meant to be one scoped task. Self-assignment from `roles.toml` is only for
sessions the human started directly at the top level.

## The resolver contract

The reference deployment resolves roles with a small script
(`resolve_role.py` beside the control-plane files) whose contract matters more
than its code:

- **It never raises to the caller.** It runs inside session-start hooks; an
  exception there would abort session start for every agent on the machine. A
  config typo must degrade to "everyone is a worker", never to "nobody can
  start a session".
- **Malformed or missing config → safe default:** orchestrator = `claude`,
  everyone else = worker, mode = `present` (the human-in-the-loop,
  least-autonomous default). Unreadable `mode.state` or an unrecognized word
  in it also degrades to `present`.
- Resolution matrix: CEO agent + `away` → `ceo`; orchestrator agent +
  `present` → `orchestrator`; everything else → `worker`.

## The optional session-start banner

A session-start hook can call the resolver and inject a
**"YOUR CURRENT ROLE: …"** banner into the agent's context, naming the role
and the playbook to load. **An injected banner outranks self-resolution** — if
you see one, obey it and skip reading `roles.toml` yourself. The banner is a
convenience, not a requirement: without hooks, the identity file's instruction
to read `roles.toml` and self-assign covers the same ground.

## roles.toml vs routing.toml — who decides what

The two TOML files divide cleanly and the precedence is fixed:

> **`roles.toml` sets the pool and who orchestrates; `routing.toml` picks
> within the pool.**

`roles.toml` is upstream: it answers "who is apex, and who *may* receive
work". `routing.toml` is downstream: given the pool, it answers "which worker
gets *this class* of task, with which model, and why". Swapping an agent into
or out of the fleet is a `roles.toml` edit; re-ranking workers as model
quality shifts is a `routing.toml` edit. Neither file hardcodes the other's
job.

`routing.toml` installs at the orchestrator runtime's config dir (reference
deployment: `~/.claude/routing.toml`); the template ships at
`config-templates/hivemind/routing.toml`.
