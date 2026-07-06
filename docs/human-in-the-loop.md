# Human-in-the-Loop Relay

How an agent escalates decisions to a human on their phone, and how to do it
safely.

The relay daemon code is **not shipped** — it is a private process that depends
on your messaging backend of choice (Telegram, Slack, Signal, SMS, etc.). This
document describes the pattern and interface contract so adopters can implement
their own.

---

## What the relay does

An agent can pause mid-task, forward a question or approval request to the
human's phone, and **block until the human responds**. From the agent's
perspective it is a synchronous call: send a structured payload, wait, receive a
decision, continue.

This is useful when:

- A permissions hook intercepts a risky action and needs human approval before
  proceeding.
- The agent reaches a genuine decision fork and needs a judgment call that should
  not be delegated to the model.
- An async notification is appropriate (task finished, anomaly detected) and no
  response is needed.

---

## Request interface

Every relay request is a structured payload. Recommended fields:

```
agent      — which agent is asking (e.g. "claude-code", "codex")
prompt     — the question or action description, full text
context    — additional background the human needs to decide
options    — list of {label, description} — never bare labels (see below)
timeout    — seconds to wait before the relay falls back (see Failure modes)
kind       — "approval" | "question" | "notification"
```

### Three payload types

| Kind | Semantics |
|---|---|
| `approval` | Binary gate. Human approves or denies a proposed action. Timeout → DENY. |
| `question` | Free-form choice or clarification. Human picks an option or types a reply. |
| `notification` | One-way. No response expected. Relay sends and returns immediately. |

---

## Full context on mobile

The relay must forward the **full description** of each option to the phone, not
just a short button label.

A bare label like "Option A" or "Proceed" is useless on a phone: the human has
no terminal in front of them and no way to reconstruct what the agent was doing.
The `description` field of each option must contain enough information for the
human to make the decision cold, from a phone notification, without context
switching back to the workstation.

Example — wrong:

```
[Approve] [Deny]
```

Example — right:

```
Action: delete 47 staged files from /project/build/
This will permanently remove the listed artifacts.

[Approve — delete the files]
[Deny — stop, do not delete]
```

The header (`prompt` + `context`) and each option's `description` must both
travel to the phone.

### Redact secrets before anything leaves the box

The payload that travels to the phone is, by construction, the *content of a
risky action* — a command line, a file path, sometimes a file excerpt. That
content can embed credentials (a token in a `curl` header, a connection string
in an env assignment). Your messaging backend (Telegram, Slack, ...) is an
**external service**: whatever you send may be stored on someone else's
infrastructure indefinitely.

So the relay must run a redaction pass over every outbound payload — pattern
match for token/key/password shapes (long high-entropy strings, `Bearer ...`,
`key=...`, PEM blocks) and replace them with placeholders **before** the send,
on your side of the wire. The human approving "run this curl command" doesn't
need the token's value to decide; they need to know a token is being sent and
to where.

---

## Presence gate

Relaying to a phone when the human is sitting at the workstation creates
unnecessary friction — a terminal prompt is faster and less disruptive. The relay
should only forward when the human is actually away.

**Relay iff:**

1. An explicit AFK flag is set, **or**
2. The workstation has been idle for ≥ N minutes (default: 420 seconds / 7 min).

### Sticky AFK flag

Provide `/afk` and `/back` toggle commands (or equivalent hooks). The flag must
be **sticky** — it stays set until explicitly cleared with `/back`. It must not
be cleared by a stray mouse movement, a screen-saver interrupt, or any automatic
idle detection. The sticky flag exists precisely because idle detection can give
false positives; human intent overrides heuristics.

Idle detection is a supplement to the flag, not a replacement for it. If the
flag says AFK, relay — regardless of what the idle timer says. If the flag says
present, do not relay — regardless of idle time.

---

## Present-mode safety

When the human is present (flag not set, idle time below threshold), the hook
**must not relay**. It must instead emit a native terminal prompt — the standard
"ask" decision that the agent runtime handles interactively.

**Critical:** a hook that exits with status 0 without emitting a decision is
treated by the agent harness as a silent approval. That means a hook that
does nothing (returns 0, prints nothing, decides nothing) will auto-approve
every action it intercepts. This is the most dangerous failure mode.

Present-mode hooks must **explicitly emit an "ask" decision** — never silently
exit 0.

```
# Correct present-mode behavior
emit_decision("ask")   # agent prompts user in terminal

# Wrong — silently exits 0 = silent allow
return 0
```

---

## Failure modes

| Failure | Correct behavior |
|---|---|
| Relay backend unreachable | Fall back to an in-terminal prompt. **There is no fallback *messaging* channel** — if no human is at the terminal either, the request blocks until timeout, then resolves DENY. |
| Human does not respond within timeout | `approval` → DENY; `question` → surface in terminal at next opportunity. |
| Idle-detection API unavailable | Treat as present (conservative default). |
| AFK flag state unknown at startup | Default to present until the human explicitly sets `/afk`. |

The timeout length is a deployment choice: a short window (minutes) fails safe to
DENY fast; the reference deployment uses a long window (~23h) so a delayed human
can still approve, at the cost of a longer block. Either way the request is
bounded — it never silently auto-approves.

The guiding principle: **default to the restrictive side**. A missed notification
is recoverable. An auto-approved destructive action may not be.

### The relay needs its own dead-man's switch

The relay is the component that fails *worst* silently: if its daemon, its
presence watcher, or the bridge they run over wedges, the human stops
receiving requests — and from their phone, "no notifications" looks identical
to "the agents don't need me." The reference deployment found its presence
watcher had been dead for **25 hours** (its scheduled task only triggered at
logon; the process was killed and nothing restarted it).

Two fixes, both required:

1. **Restart paths for every relay component** — run-on-schedule keep-alive
   triggers plus restart-on-failure, not just run-at-logon.
2. **An independent dead-man's switch** — a separate, minimal watchdog on a
   different mechanism (different scheduler entry, different runtime, no
   shared bridge) that checks the relay's heartbeat file and daemon liveness,
   and pages the human *directly* through the messaging API when they go
   stale. It must not depend on any component it monitors.

The generalization: anything that gates approvals needs a liveness alarm that
does not share its failure modes. A watchdog that dies with its ward is
decoration.

---

## Wiring into the permissions hook

The relay plugs into the same hook system as the permissions protocol
(see `docs/permissions-protocol.md`). When a permissions hook fires:

1. Check presence gate.
2. If away → serialize the action into a relay payload, send, block.
3. If present → emit "ask" to terminal.
4. Relay response or terminal response → return the decision to the hook.

The hook's job is to return a decision, not to make one itself. The relay is just
the channel through which the human's decision arrives.
