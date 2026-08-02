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

## Presence gate — the relay presence (AFK) toggle

Relaying to a phone when the human is sitting at the workstation creates
unnecessary friction — a terminal prompt is faster and less disruptive. The relay
should only forward when the human is actually away.

> **Naming warning:** this is the **relay presence (AFK) toggle** — whether
> approval/question traffic goes to the phone. It is *not* the hivemind
> `mode.state = away` concept documented elsewhere in this repo, which
> re-seats the CEO-apex role in the agent hierarchy. Same word "away", two
> unrelated switches.

The gate has **three states, in strict precedence**:

1. **Force-off (mute)** — highest priority. Relay disabled entirely; nothing
   goes to the phone regardless of any other signal. Settable from the
   dashboard. Because the *same* gate is consulted by the relay's 2-second
   abort-poll (below), flipping force-off also **releases hooks already
   blocked waiting on a phone answer** — they withdraw the phone request and
   fall through to the native terminal prompt. Muting is therefore also the
   "un-stick a wedged approval" lever.
2. **Sticky `/afk` flag** — human-declared away. Relay regardless of what the
   idle timer says.
3. **Idle threshold** — no flag set: relay iff the workstation has been idle
   ≥ N minutes (default: 420 seconds / 7 min).

### Sticky AFK flag

Provide `/afk` and `/back` toggle commands (or equivalent hooks). The flag must
be **sticky** — it stays set until explicitly cleared with `/back`. It must not
be cleared by a stray mouse movement, a screen-saver interrupt, or any automatic
idle detection. The sticky flag exists precisely because idle detection can give
false positives; human intent overrides heuristics.

Idle detection is a supplement to the flag, not a replacement for it. If the
flag says AFK, relay — regardless of what the idle timer says. If the flag says
present, do not relay — regardless of idle time.

### The return-to-keyboard escape

A request already sent to the phone must not strand the human who has since
walked back to the workstation. While a relay wait is open, the daemon
**re-polls the presence gate every ~2 seconds**. If keyboard/mouse activity
resumes (and no sticky `/afk` flag is set), the relay **withdraws the phone
request** and the hook falls through to the native terminal prompt — the
human answers where they actually are. The same 2s poll is what makes
force-off release in-flight waits (state 1 above).

### The cheap presence signal pattern

Live-probing idle time can be expensive (a cross-boundary call, a GUI API).
Instead, a **host-side watcher** writes a small heartbeat file every ~15
seconds:

```json
{ "idle_seconds": 12, "written_at": 1722600000 }
```

The relay reads the file — a cheap local read — and only falls back to an
expensive live probe when the beat is **stale** (`written_at` older than
~60 s). The trust window must tolerate a small *negative* clock skew: after
the host sleeps and wakes, `written_at` can briefly appear to be in the
future; treat small negative skew as fresh, not as corruption.

### The cheap gate before an expensive bridge pattern

When the relay lives across a boundary (e.g. a WSL instance reached from
Windows hooks), do not pay the bridge cost on every tool call. Put a
**native fast-exit gate script** in front of the cross-boundary spawn: it
checks locally whether this call could possibly need relaying (presence
state, rule match) and exits immediately if not. Un-relayed calls — the vast
majority — then cost ~0 instead of a full cross-boundary process spawn each
time.

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

## The AskUserQuestion redirect

Approvals are not the only thing worth relaying. When the agent asks a
multiple-choice question mid-task (Claude Code's `AskUserQuestion` tool), an
AFK human never sees the terminal picker — the turn just stalls. The fix: a
`PreToolUse` hook **intercepts the question tool itself** and forwards the
question + options to the phone.

### The exit-2 / stderr answer channel

The subtle part is getting the answer *back in*. A `PreToolUse` hook can
allow or block a tool call, but it **cannot substitute a tool result** — there
is no hook mechanism to make `AskUserQuestion` "return" the phone's answer.
The contract that works:

1. Hook intercepts the question, relays it, blocks until the phone answers.
2. Hook **exits 2** (block the tool call) with the answers on **stderr**.
3. The stderr text is formatted as an *instruction to the model*: "the human
   answered: <answers>. Use these answers verbatim. Do NOT retry the
   question tool."

The block-with-payload *is* the answer-injection channel. Two failure shapes
to avoid: exit 2 with a bare "denied" makes the agent re-ask in a loop; exit
0 lets the native picker fire and the phone answer is lost.

### Questions fail OPEN; approvals fail CLOSED

This is a deliberate asymmetry:

- An **approval** guards a risky action. If the relay times out, crashes, or
  returns garbage, the safe direction is **DENY** — fail closed.
- A **question** guards nothing; it is a request for preference. Denying it
  just wedges the turn. So on *any* degraded outcome — relay timeout, daemon
  down, adapter crash, malformed response, or the human tapping "Skip" on the
  phone — the hook steps aside (exit 0, no decision) and the **native
  terminal picker** fires as if the hook weren't there. Fail **open**, to the
  native UI.

Worst case for a failed question relay: the picker waits at the terminal
until someone returns. Worst case for a failed-open approval: an unreviewed
destructive action. Different stakes, different defaults.

---

## Turn-end pings (Stop-event mirror)

The third relay surface: knowing the agent *finished* — and steering it —
without walking back to the desk.

- A **Stop-event hook** fires when the agent ends its turn. When the presence
  gate says away, it mirrors the last assistant message to the phone as a
  notification.
- A **phone reply** to that ping is injected as the next user turn: the hook
  returns `decision: "block"` with the reply text as the `reason`. The
  runtime treats the block reason as instruction, so the agent continues
  with the human's reply as if it had been typed at the terminal.
- No reply → the hook returns nothing and the turn ends normally.

**Timeout rule:** the hook's configured timeout must be **≥ the adapter's
answer window** (reference deployment: 86 400 s ≈ 24 h). A short hook timeout
(e.g. the 600 s many examples ship) means the runtime kills the hook while
the adapter is still waiting — a phone answer sent 11 minutes later is
**stranded**: the adapter records it, but the hook that could have delivered
it is gone. The same rule applies to the `AskUserQuestion` hook entry.

---

## Failure modes

Failure behavior differs by payload kind — approvals fail **closed**,
questions fail **open** to the native UI (see the AskUserQuestion section for
why).

**`approval` payloads (fail CLOSED):**

| Failure | Correct behavior |
|---|---|
| Relay backend unreachable | Fall back to an in-terminal prompt. **There is no fallback *messaging* channel** — if no human is at the terminal either, the request blocks until timeout, then resolves DENY. |
| Human does not respond within timeout | DENY. Never auto-approve. |
| Malformed / unverifiable response | DENY (see the signed-response verifier below — it fails closed on any missing key or bad signature). |

**`question` payloads (fail OPEN to native UI):**

| Failure | Correct behavior |
|---|---|
| Relay backend unreachable / adapter crash | Hook steps aside; native terminal picker fires. |
| Timeout, malformed response, or phone "Skip" | Same — fall through to the native picker. The question is never force-answered or force-denied. |

**Presence / infrastructure:**

| Failure | Correct behavior |
|---|---|
| Idle-detection API unavailable | Treat as present — no page (current doctrine; but see the open tension below). |
| AFK flag state unknown at startup | Default to present until the human explicitly sets `/afk`. |
| Heartbeat file stale (>~60 s) | Fall back to a live presence probe, not to a guess. |

The timeout length is a deployment choice: a short window (minutes) fails safe to
DENY fast; the reference deployment uses a long window (~23h) so a delayed human
can still approve, at the cost of a longer block. Either way the request is
bounded — it never silently auto-approves.

The guiding principle: **default to the restrictive side**. A missed notification
is recoverable. An auto-approved destructive action may not be.

### The channel-parity lesson

Historical bug: a bare-digit phone reply ("2") was recorded *literally* as
the answer, while the same reply at the terminal was resolved to the option
*label* it selected. The agent then acted on the string "2". The rule:
**every input channel must resolve replies through the same grammar** — one
parser, shared by terminal and phone paths, mapping digits/labels/free text
to the same canonical answer. Standing habit on top of the fix: confirm
high-stakes forks in plain text, not with a bare number.

### Open tension: which way should idle-detection failure fail?

Current doctrine (table above) fails toward **present** — no page — on the
grounds that a spurious page is friction. A cross-model review argued the
opposite: under *bounded staleness* (the signal is known-broken, not merely
quiet), failing toward **paging** is safer, because a missed page is the
catastrophic direction — the human believes they're reachable and they are
not. This is presented here as an **open question**, not settled doctrine.
Pick a side deliberately for your deployment and write it down.

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

Two hard-won refinements:

- **Re-warn cadence, not warn-once.** The reference deployment's watchdog
  originally warned once per failure and went quiet; a 15-minute outage
  became silence after the first ping — indistinguishable from "all fine".
  Now it re-warns every 300 s for as long as heartbeat writes keep failing.
  A watchdog whose failure mode is silence is not a watchdog.
- **Push, not probe.** The daemon *pushes* its heartbeat to a world-readable
  location on the host, rather than the watchdog probing into the daemon's
  environment — because a SYSTEM-account watchdog cannot see into a per-user
  WSL instance. When monitor and monitored live in different security
  contexts, the monitored side must publish to ground the monitor can reach.

---

## Relay security model

The relay is a remote-control channel for approving agent actions — it must
be treated as attack surface, not plumbing. Five protections, all live in the
reference deployment, plus the threat model each answers.

### 1. Chat-ID allowlist

Threat: a stranger finds the bot and messages it. The daemon holds exactly
**one allowed chat ID**. Updates from any other chat are **dropped silently**:
no button tap honored, no reply consumed, no error message that would confirm
the bot exists. Outbound messages are pinned to the same single ID — the
daemon *cannot* be talked into messaging a different chat.

### 2. Signed approval responses

Threat: a process on the workstation forges an "approved" response into the
mailbox. The daemon signs each response — over the tuple
`(id, nonce, decision, expires_at)`, serialized as **canonical sorted-key
JSON** — with an **Ed25519** private key; the hook-side adapter verifies with
the public key.

Asymmetric was chosen over HMAC *deliberately*: the verifier runs as the
agent's own user, so any key the verifier holds is readable by an injected
agent process. With HMAC, the verify key **is** the forge key — a same-user
attacker could mint approvals. With Ed25519 the adapter holds only the public
key, which verifies but cannot sign.

### 3. Replay protection

Threat: yesterday's legitimate "approve" is replayed against today's request.
Each request carries a fresh **nonce**; the response echoes it *under the
signature*, and the expiry is signed too. The verifier **fails closed** on
any missing/corrupt key material or bad signature — a broken verifier denies,
it never waves through.

### 4. Privilege separation

Threat: the agent (or anything running as the agent's user) reads the bot
token or rewrites the daemon's config. The daemon runs under a **dedicated
non-agent UNIX account**; its config is `chmod 600` and the config loader
**refuses to start** on looser modes. Running the daemon as your own user
leaves responses forgeable and the token readable — this separation is **not
optional for a real deploy**.

### 5. Log hygiene

Threat: the bot token leaks through logs. A **token-redacting log formatter**
scrubs the token from every log record. Plus the ordering hazard: config
errors raised *before* the formatter installs bypass it — those early-path
messages must be written to never contain the token in the first place.
Redaction you install late doesn't cover the lines emitted early.

### Additional guards

- **Stale-tap guard.** A phone tap that arrives *after* the request already
  resolved (e.g. timed out to auto-deny) must not display as "approved ✓" —
  the human would believe they gated an action that in fact already denied
  (or worse, believe they approved something that ran). Late taps get an
  explicit "expired" acknowledgment, and a janitor sweeps orphaned response
  files so they can't be matched to future requests.
- **Session-tag addressing.** With multiple concurrent agent sessions, a bare
  reply is ambiguous. A registry maps `(agent, session)` → a human tag
  ("Claude 1", "Codex 2"); outbound messages carry the tag and replies route
  back to the right session.
- **Scope boundary.** This is a **single-operator, single-chat** design: one
  human, one phone, one allowlisted chat. None of the mechanisms above are
  hardened for multiple mutually-untrusting operators — do **not** deploy it
  multi-tenant.

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
