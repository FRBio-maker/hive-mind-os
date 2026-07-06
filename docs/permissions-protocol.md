# Permissions Protocol

How permission decisions flow across Claude Code, Codex CLI, and Gemini CLI —
the cross-agent model.

## The shared decision tree

For any tool an agent wants to use, the decision flows:

```
                  ┌──────────────────────────────────┐
                  │  Agent decides to call a tool    │
                  └────────────────┬─────────────────┘
                                   │
                                   ▼
                  ┌──────────────────────────────────┐
                  │  Hook fires (if registered)      │
                  │                                  │
                  │  Adapter loads user's permission │
                  │  rules → match against tool_input│
                  └────────────────┬─────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
            DENY                  ASK                ALLOW
              │                    │                    │
              ▼                    ▼                    ▼
       Block silently      Relay to approval      Proceed silently
       (exit 2 / deny)     channel, await tap     (exit 0 / allow)
                                   │
                            ┌──────┴──────┐
                            │             │
                         Approve        Deny
                            │             │
                            ▼             ▼
                       Proceed         Block
```

Same shape for all three agents. The implementation differs per runtime.

## The three gates

### ALLOW — silent proceed

Known-safe operations that match an explicit allow rule proceed without any
prompt. Examples:
- `git status`, `git log`, `git diff` (read-only git)
- `npm ls`, `pip list` (read-only package queries)
- Any Bash pattern in the agent's `fewer-prompts` allowlist

### ASK — escalate to relay

Anything potentially impactful that matches an ask rule — or that the
`defaultMode=auto` classifier judges risky (see below) — escalates to the human
via the approval relay. Examples:
- Writes inside the wiki vault or tracked repos
- Dependency installs (`npm install`, `pip install`)
- Secrets-adjacent reads (`.env`, cloud credential files)
- `curl | sh`, `wget | bash` (pipe-to-shell patterns)
- Non-main force pushes

**Unmatched pattern → auto-classified.** This is the `defaultMode=auto`
setting: a classifier sorts calls that match no explicit rule — clearly-safe,
routine ones run silently, while anything risky or ambiguous escalates to ASK.
Dangerous operations don't slip through, and routine work isn't interrupted.
(Not every runtime has this classifier — see the per-runtime note below.)

### DENY — hard block (silent)

Some operations are blocked unconditionally, with no relay escalation:
- Apocalypse commands: `rm -rf /`, `dd of=/dev/sd*` (and other raw disk
  devices), anything targeting the root filesystem or raw devices
- Auth-token reads: SSH private keys (`~/.ssh/id_*`), `gh auth token`, and
  credential stores like `.credentials.json`. (Credential-*adjacent* reads —
  `.env`, `~/.aws`, `~/.npmrc`, `~/.kube/config` — are **ASK**, not deny, so a
  legitimate read can be approved rather than hard-blocked.)
- `git push --force` to the main/master branch (non-main force pushes are ASK)
- Commits with `--no-verify` or `--no-gpg-sign` without explicit human
  authorization

Hard denies are silent — the agent is blocked but no relay notification fires.
This prevents the phone from buzzing on clearly-off-limits operations.

## defaultMode=auto — the classifier idea

The `defaultMode` setting controls what happens to tool calls that don't match
any explicit rule:

- `auto` (recommended default) — unmatched patterns go through the classifier:
  clearly-safe calls run, risky/ambiguous ones → ASK. Balanced: routine work is
  silent, dangerous edge cases still surface. On runtimes without a classifier
  (e.g. Gemini), unmatched calls fall to the runtime's native approval mode
  (which prompts for shell) — the shipped policy adds no blanket-allow, so add
  narrow allow rules only for routine tools you trust, never a catch-all allow.
- `allowAll` / equivalent — unknown patterns → ALLOW. Convenient but risky:
  any gap in the rule set becomes a silent permit.
- `deny` — unknown patterns → DENY. Useful for strict sandboxes but requires
  a comprehensive allowlist or the agent grinds to a halt on routine work.

**Recommendation:** start with `defaultMode=auto`. Over time, use the
`fewer-permission-prompts` skill (or equivalent) to promote recurring
known-safe patterns into the explicit allowlist, trimming phone interruptions
without lowering the security floor.

## Ask-list-first

When designing the rule set itself, prefer an **explicit ask-list** as the
primary architecture over "broad allow + narrow deny." The difference is which
direction mistakes fail:

- Broad-allow + narrow-deny: any *gap* in your deny list is a silent permit.
- Ask-list-first: the safe path is the *prompted* path — a gap costs you an
  extra approval tap, not an unreviewed action.

Grow the allow-list from evidence (patterns you actually approved repeatedly),
not from anticipation. This composes with `defaultMode=auto`: explicit ask
rules for the risk classes you know about, the classifier for the ones you
didn't think of, and a slowly-earned allow-list underneath both.

## Timeout-to-deny safety

When an ASK escalates to the relay and the user does not respond within the
configured timeout, the decision resolves as **DENY** automatically. The agent
never silently auto-approves a timed-out request. The timeout length is a
deployment choice: a short window (minutes) fails safe to DENY quickly; a long
window — the reference deployment uses ~23 hours — keeps the request open so a
delayed human can still approve, at the cost of a longer block. Either way the
request is bounded and resolves to DENY if unanswered.

If the relay itself is unreachable (daemon down, notification API unavailable),
the agent falls back to an in-terminal prompt rather than blocking indefinitely
or defaulting to allow. Note there is **no fallback *messaging* channel** — the
terminal fallback only helps if a human is actually at the terminal. A
truly-AFK agent whose relay is down will block until the timeout, then DENY.

## Agents must not self-modify the permission surface

An agent must not edit its own permission settings files, hooks, or relay
adapter config without explicit human authorization. Doing so would allow an
agent to grant itself expanded permissions — violating the human-in-the-loop
guarantee. The permission surface is the human's to control; the agent's job
is to operate within it.

Any edit to `~/.claude/settings.json` (permissions block), `~/.codex/config.toml`
(approval policy), `~/.gemini/policies/`, or relay adapter config files is an
ASK-class operation — it escalates to the human.

## Shell subexpression caveat

Commands containing a `$()` shell subexpression **always trigger a permission
prompt**, regardless of other allow rules. This is a hardcoded safety gate in
the agent harness, not a configurable setting.

In practice: avoid wrapping known-safe Bash commands in cosmetic `$()` just for
string interpolation or convenience. The subexpression triggers a prompt even
when the underlying command is on the allowlist. Rewrite to avoid `$()` where
you want silent execution, or accept the prompt.

## Wrapper tunneling — rules must see through shells

If your relay adapter (or any custom rule layer) matches rules against the
*outer* command string, every rule is trivially bypassed by wrapping:
`bash -c '<risky>'`, `wsl -e sh -c '<risky>'`, `/bin/bash -c '<risky>'`
(absolute-path shells escape name-based matching), prefix launchers
(`sudo`/`env`/`nohup`/`setsid <risky>` — including a launcher wrapping a
non-shell command directly), and command substitution (`$(<risky>)`,
`` `<risky>` ``). The reference implementation closed each of these
individually, found late, after review — treat this list as the *starting*
test suite for your own adapter, and make unrecognized wrapper forms
**fail to ASK**, never to allow.

Be honest about the ceiling: a static command parser stops accidents and naive
injection, not a determined adversary — there are always more encodings. The
hard floor underneath it is the runtime's own gates plus OS-level separation
(don't let agent processes read the relay's credentials; see
`docs/human-in-the-loop.md`).

## Per-agent implementation notes

### Claude Code

- Hook: `PreToolUse` in `~/.claude/settings.json`.
- Permission rules: `permissions.{allow,ask,deny,defaultMode}` block.
- Hook payload: JSON on stdin with `tool_name`, `tool_input`, `cwd`.
- Adapter response: exit 0 (allow), exit 2 (deny).
- **Important:** `PreToolUse` fires on every matched tool call regardless of
  permission state. The relay adapter must mirror the `ask`/`deny` rules
  itself and short-circuit non-matching calls — otherwise the phone buzzes on
  every routine `pwd` or `ls`.

### Codex CLI

- Hook: `PermissionRequest` in `~/.codex/config.toml`.
- Permission rules: `approval_policy`, `sandbox_mode`, `[projects.X]` trust
  tables.
- Hook payload: JSON on stdin with `session_id`, `turn_id`, `tool_name`,
  `tool_input`, `cwd`, `permission_mode`.
- Adapter response: stdout JSON with
  `hookSpecificOutput.decision.behavior` ∈ `{"allow", "deny"}`.
- **Note:** Codex's `PermissionRequest` only fires on actual approval prompts —
  Codex pre-filters. The relay adapter still includes its own filter for
  defense-in-depth and rule consistency across agents.
- **First-run trust:** Codex prompts to TRUST any new hook command once; the
  trust hash lives in `[hooks.state]` in the config. Don't copy that table
  across machines.

### Gemini CLI

- Hook: `BeforeTool` in `~/.gemini/settings.json`.
- Permission rules: TOML policy files in `~/.gemini/policies/*.toml`.
- Hook payload: JSON on stdin with `tool_name`, `tool_input`, `cwd`,
  `session_id`, `transcript_path`.
- Adapter response: stdout JSON with `decision: "allow"` or `decision: "deny"`
  plus `reason`.
- **Important:** Gemini's `defaultApprovalMode` rejects `"yolo"` with an enum
  error — yolo is a CLI flag only. To fully bypass Gemini's native terminal
  prompts (so the relay is the sole gate), launch with `--yolo`. Without it,
  Gemini still prompts in-terminal for shell commands even when the policy
  catch-all says `decision = "allow"`.
- **Catch-all trap:** the policy catch-all (`toolName = "*"`) must NOT include
  `phone_decision = "ask_user"`, or every routine tool call buzzes the phone.
  Use plain `decision = "allow"` for the catch-all; only specific high-risk
  rules carry `phone_decision = "ask_user"`.

## Why mirror the same rules across all three agents

Three reasons:

1. **User mental model.** "A read of `.ssh` is risky" — true regardless of
   which CLI makes the call. The cross-agent mirror keeps the user from learning
   three separate ask/deny vocabularies.
2. **One relay, one source of truth.** All three adapters call into the same
   permission-rules checker in the relay repo. It reads Claude's
   `permissions.ask` block and Gemini's TOML policies; Codex tool names get
   aliased to Claude tool names. A rule defined once propagates everywhere.
3. **Audit trail.** When the user gets a relay notification, it identifies the
   agent making the request. The decision file in the mailbox carries the agent
   name. The user can review post-hoc what each agent has been doing.

## Cross-references

- `permissions/README.md` — file-by-file snapshot and merge instructions.
- `permissions/` — the actual rule excerpts, flat and OS-agnostic:
  `codex-config.permissions.toml`, `grok-config.permissions.toml`, and
  `gemini-policies/` (TOML/JSON).
- `docs/INFRASTRUCTURE.md` Panel 4 — the permission pipeline Mermaid diagram.
- `docs/human-in-the-loop.md` — relay setup guide.
