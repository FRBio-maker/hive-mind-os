---
description: Force the phone relay ON (sticky) until /back — question prompts, approval prompts, and turn-end pings route to your phone regardless of keyboard/mouse activity.
argument-hint: (no arguments)
---

<!--
TEMPLATE NOTE — the CONTRACT section below is normative: any implementation of
/afk must satisfy it. The reference implementation is one concrete way the
reference fleet does it (Windows host + a Linux subsystem running the relay
adapters, messaging via a phone-relay bot such as Telegram) — localize paths,
flag locations, and the messaging channel to your own setup.
-->

Turn ON the sticky AFK relay flag, then confirm to the user in one line.

## The flag-file contract (normative)

The relay's mode is decided entirely by **four flag files** — two pairs, one
flag per pair in each environment the relay spans (adapter side + host side):

| Flag | Side | Meaning |
|---|---|---|
| `<presence-dir>/afk` | adapter | sticky ON — relay everything |
| `<your-home>/.claude/relay-on.flag` (content `sticky`) | host | fast gate: hooks spawn the relay adapter only when this exists; `sticky` tells the presence watcher never to auto-delete it |
| `<presence-dir>/relay-off` | adapter | force-off — relay nothing |
| `<your-home>/.claude/relay-off.flag` | host | force-off, host side (settable from the dashboard) |

**Precedence: force-off > sticky > idle.** The relay's `should_relay()` check
resolves in that order. With no flags at all, the relay is **idle-gated**: a
presence watcher creates the host gate flag (content `idle`) only after the
user has been idle past a threshold (default 420 s; env
`RELAY_PRESENCE_IDLE_SECS`), and deletes it when activity resumes.

**/afk sets the sticky pair AND deletes both force-off flags.** The deletion
is mandatory: force-off beats sticky, so a stale force-off flag left behind
would make /afk silently do nothing.

**Sticky means sticky:** a stray mouse move or keystroke must NOT cancel it
(unlike the idle timer). It stays on until `/back`.

While the sticky flags exist, EVERY relay channel — question prompts, risky-
tool approval prompts, and turn-end pings — routes to the phone instead of the
terminal.

## Reference implementation (localize)

Run one command that, atomically enough for this purpose:

1. Ensures `<presence-dir>` exists.
2. Deletes `<presence-dir>/relay-off` and
   `<your-home>/.claude/relay-off.flag` (ignore if absent).
3. Creates empty `<presence-dir>/afk`.
4. Writes `<your-home>/.claude/relay-on.flag` with content `sticky`.
5. Echoes a confirmation naming the flags it set/cleared.

On the reference fleet the relay adapters run inside a Linux subsystem on the
Windows host, so `<presence-dir>` lives in the subsystem's home and the
`.claude` gate flags live on the host filesystem — one shell invocation from
the host into the subsystem does all five steps. A single-environment setup
can point both sides at the same directory.

Show the command's real output. **If it fails or returns non-zero, tell the
user plainly that AFK is NOT active** — never let them walk away thinking
they're covered when they aren't.
