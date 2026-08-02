# permissions/

One permission model, mirrored across runtimes. These files express a
single set of rules — **what runs silently, what asks for approval (and
where), and what's blocked outright** — translated into the native format
each agent understands.

```
permissions/
├── README.md                            ← you are here
├── claude-settings.permissions.json     ← ~/.claude/settings.json excerpt
├── codex-config.permissions.toml        ← ~/.codex/config.toml excerpt
├── gemini-settings.permissions.json     ← ~/.gemini/settings.json excerpt
├── grok-config.permissions.toml         ← ~/.grok/config.toml excerpt
└── gemini-policies/
    └── claude-mirror.toml                ← drop-in at ~/.gemini/policies/
```

## One source of truth, mirrored across runtimes

The hive runs one permission model. The hard part is that each agent
enforces permissions differently:

- **Claude** uses a `permissions.allow/ask/deny` list in `settings.json`.
- **Gemini** uses TOML policy files plus a `defaultApprovalMode`.
- **Codex** uses its built-in `PermissionRequest` approval event.
- **Grok** reads the Claude settings (in compatibility mode) and
  translates them into native rules, with a `permission_mode` fallback.

So there is one *model* expressed four ways. The same risky-thing
patterns — `rm -rf` of root/home, `dd` to raw disks, SSH private-key and
credential reads, `gh auth token`, `curl | sh`, force-push to main,
`--no-verify` commits — **should appear** in each *pattern-based* file
(Claude, Gemini, and Grok-via-Claude-compat). **Codex is the exception:** its
`config.toml` carries no inline allow/ask/deny lists — it routes every
command through its built-in `PermissionRequest` approval event (plus the
relay), so the same rules are enforced by the approval flow rather than
expressed as patterns. Change the model in one place and you must mirror it
into the other pattern-based files.

**Drift is expected, not hypothetical.** Without a verify script diffing
each excerpt against the live config, published canon and any live
deployment *will* diverge — a 2026-08 audit of the reference deployment
found exactly that: the live Claude deny list had silently shrunk to a
subset of the canon here (`rm -rf` variants + credential-file reads),
dropping raw-disk `dd`, `gh auth token`, force-push-to-main and
`--no-verify` without anyone noticing. The full set was restored the same
day (2026-08-02), but the deny set in these files remains the canon;
assume any live deployment lags it until a `verify.sh` exists (not built
yet) or you've diffed by hand.

### Windows deployments — mirror every rule into PowerShell

On Windows, Claude Code exposes **PowerShell as a distinct tool** alongside
Bash. Permission rules match per-tool: a `Bash(...)`-only ruleset is
**silently bypassed by every PowerShell call** — the deny/ask patterns
simply never match. `claude-settings.permissions.json` therefore carries a
`PowerShell(...)` mirror of every Bash rule, plus PowerShell-specific
patterns (`Remove-Item -Recurse -Force` home variants in deny;
`Invoke-Expression` / `| iex` shell-eval in ask). If you add a Bash rule,
add its PowerShell twin in the same commit.

## These are excerpts, not whole files

The Claude/Codex/Gemini files here are **excerpts** — only the
permission and hook keys. The live config files also carry
machine-specific content (MCP servers, plugin lists, themes, status
lines). To apply on a new machine, **merge** these keys into your live
config rather than replacing the file. The Gemini policy TOMLs in
`gemini-policies/` are self-contained and **fail safe by default** — risky
reads and commands prompt in-terminal (`decision="ask_user"`). Copy them to
the path your `policyPaths` points at. If you wire an approval relay, you can
flip those rules to route to your phone instead (see the file's own comments).

## The model: Deny / Ask / Auto

| Category | Examples | Behavior |
|---|---|---|
| Deny | `rm -rf` root/home, `dd` to raw disks, SSH private keys (`.ssh/id_*`), `.credentials.json`, `gh auth token`, force-push to main, `--no-verify` commits | Block silently. Never prompt, never run. |
| Ask  | `curl x \| sh`, force-push, reads of `~/.ssh/**` `~/.env*` | Pause for approval. Optionally routed to a secondary channel via a relay hook. |
| Auto | everything else | Routed through `defaultMode=auto` — a classifier runs clearly-safe calls silently and escalates risky/ambiguous ones to Ask. (Gemini has no classifier: the shipped policy ships **no** blanket-allow catch-all, so unmatched calls fall to its native `defaultApprovalMode`, which prompts for shell. Keep the deny/ask rules comprehensive there.) |

*Reference deployment status:* the Deny row above is recommended canon and
has been enforced in full on the reference deployment since 2026-08-02 (see
"Drift is expected" above for the lapse that prompted the restore). Applying
these files as published gives you the full set.

The **Ask** tier can either prompt in-terminal or, if you wire up a
human-in-the-loop relay (see `../docs/human-in-the-loop.md`), route to a
secondary channel like your phone. The hook commands in these excerpts
are placeholders (`<your-relay-command>`) — point them at your own relay,
or delete the hook blocks to keep approvals in-terminal.

## Per-agent application notes

### Claude — `~/.claude/settings.json`
Merge the `permissions` block and (optionally) the `hooks.PreToolUse`
relay entries. Append to any existing `PreToolUse` array — don't replace
it.

### Codex — `~/.codex/config.toml`
Merge `exec_permission_approvals`, your `[projects.'...']` trust blocks
(substitute your own paths), and optionally the `[[hooks.PermissionRequest]]`
relay block (append, don't replace). Don't copy `[hooks.state]` blocks —
Codex regenerates trust hashes per machine.

### Gemini — `~/.gemini/settings.json`
Merge `policyPaths`, `general.defaultApprovalMode` (`"auto_edit"`), and
optionally the `hooks.BeforeTool` relay entry. Then drop the contents of
`gemini-policies/` at the path `policyPaths` points to. Gemini timeouts
are in **milliseconds**.

### Grok — `~/.grok/config.toml`
Grok needs almost nothing copied: in Claude-compatibility mode it reads
the Claude settings and translates the rules automatically. Set only the
prompt-policy fallback: `[ui].permission_mode = "default"`. Avoid Grok's
`"auto"` mode — it's flagged experimental.

See `../docs/permissions-protocol.md` for the full cross-agent model.
