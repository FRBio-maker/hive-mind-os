---
description: Turn the sticky AFK relay OFF — fall back to idle-based gating (relay only kicks in after the idle threshold, default ~7 min of no keyboard/mouse activity).
argument-hint: (no arguments)
---

<!--
TEMPLATE NOTE — the CONTRACT section below is normative; the reference
implementation is the reference fleet's concrete version (Windows host +
Linux subsystem). Localize paths and flag locations. See commands/afk.md for
the full four-flag table.
-->

Turn OFF the sticky AFK relay flag, then confirm to the user in one line.

## The contract (normative)

**/back removes ALL FOUR mode flag files** — the sticky pair
(`<presence-dir>/afk` + `<your-home>/.claude/relay-on.flag`) AND the
force-off pair (`<presence-dir>/relay-off` +
`<your-home>/.claude/relay-off.flag`).

`/back` means "return to the default", not "turn the relay off": with all
flags gone, the relay reverts to **idle-based gating** — the presence watcher
re-creates the host gate flag (content `idle`) once the user has been idle
past the threshold (default 420 s = 7 min; env `RELAY_PRESENCE_IDLE_SECS`),
and questions/approvals/pings then route to the phone. While the user is
actively at the keyboard, prompts stay in the terminal — no phone buzzing,
and tool hooks skip spawning the relay adapter entirely.

Precedence recap (from `afk.md`): **force-off > sticky > idle.** Clearing all
four flags is what lands the system cleanly in the idle-gated default state.

**Idempotent by design:** removal must succeed quietly when a flag is already
absent (`rm -f` semantics), so running `/back` twice is harmless.

## Reference implementation (localize)

Run one command that force-removes all four flag files (ignoring missing
ones) and echoes a confirmation, e.g. "AFK OFF — all mode flags cleared
(sticky + force-off, both sides); relay now idle-gated (~7 min)." On the
reference fleet this is one shell invocation from the Windows host into the
Linux subsystem where the presence directory lives; a single-environment
setup deletes from one directory.

Show the command's real output. If it fails, say plainly that the sticky
relay may still be active.
