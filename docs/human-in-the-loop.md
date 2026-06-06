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
| Relay backend unreachable | Fall back to terminal prompt. Never block forever. |
| Human does not respond within timeout | `approval` → DENY; `question` → surface in terminal at next opportunity. |
| Idle-detection API unavailable | Treat as present (conservative default). |
| AFK flag state unknown at startup | Default to present until the human explicitly sets `/afk`. |

The guiding principle: **default to the restrictive side**. A missed notification
is recoverable. An auto-approved destructive action may not be.

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
