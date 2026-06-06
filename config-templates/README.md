# config-templates/

Minimal, illustrative runtime configs for each agent in the hive. These
are **templates, not drop-in files** — they show the shape and the few
fields that matter, with generic placeholder paths. Adopt the pieces you
want by merging them into your live config; don't blindly overwrite a
working config file with these.

```
config-templates/
├── README.md            ← you are here
├── claude/settings.json ← Claude Code: ~/.claude/settings.json
├── codex/config.toml    ← Codex CLI:  ~/.codex/config.toml
├── gemini/settings.json ← Gemini CLI: ~/.gemini/settings.json
└── grok/config.toml     ← Grok CLI:   ~/.grok/config.toml
```

A note on placeholders: substitute `$HOME`, `~/`, `<your-vault>`, and
`<your-project-path>` with your real locations before use. The templates
ship with placeholders on purpose so nothing private is baked in.

## A note on JSON and comments

JSON has no comment syntax, so the Claude and Gemini `settings.json`
templates can't document themselves inline. That's what this README is
for — the field-by-field notes below. The Codex `config.toml` *can*
carry comments (TOML supports `#`), so it documents itself.

## claude/settings.json

Claude Code reads `~/.claude/settings.json` at startup.

- **`permissions.defaultMode`** — `"auto"` routes calls that aren't explicitly
  flagged through a classifier (clearly-safe → run, risky/ambiguous → ask). The
  `allow` / `ask` / `deny` lists are explicit overrides. See `../permissions/`
  for the fuller rule set and the cross-agent model.
  - `allow` — patterns that run silently (here: all reads).
  - `ask` — patterns that pause for confirmation (credential-dir reads,
    piped-shell installers, force-push).
  - `deny` — patterns blocked outright, never prompted (`rm -rf` of root
    or home, credential files).
- **`hooks.SessionStart`** — one illustrative hook that runs a
  session-start script at a generic path (`$HOME/<your-vault>/scripts/
  session_start_hook.py`). This is where you'd wire in a manifest
  regenerator or context injector. A working example of that script
  lives at `wiki-template/scripts/session_start_hook.py` — it builds
  the manifest and prints it to stdout so the runtime can inject it
  into context. Point the hook path at your copy once you've placed the
  vault, or delete the block if you don't run one. Add your own hooks
  (and any hooks tied to plugins or external tooling) here.

## codex/config.toml

Codex CLI reads `~/.codex/config.toml`.

- **`exec_permission_approvals = true`** — routes command execution
  through Codex's approval flow instead of auto-running everything.
- **`[projects.'<your-project-path>']` / `trust_level`** — auto-trust
  specific directories so Codex doesn't re-prompt each session.
  Substitute your own paths; add one block per trusted project.

## gemini/settings.json

Gemini CLI reads `~/.gemini/settings.json`. Note: Gemini hook timeouts
are in **milliseconds**, not seconds.

- **`general.defaultApprovalMode`** — `"auto_edit"` auto-approves edits
  but still prompts for shell commands. (Don't set `"yolo"` here — it's
  a CLI flag only and errors at startup if placed in settings.)
- **`policyPaths`** — where Gemini loads its TOML permission policies
  from. See `../permissions/.../gemini-policies/` for the policy files
  that go at this path.
- **`hooks.SessionStart`** — same illustrative session-start hook as the
  Claude template. Point it at your own script or remove it.

## grok/config.toml

Grok CLI reads `~/.grok/config.toml`. Grok runs in Claude-compatibility mode
and reads its house rules from `~/.grok/AGENTS.md` (bootstrap symlinks
`identity/GROK.md` there), so this file carries only runtime knobs, not persona.

- **`[ui] permission_mode`** — `"default"` is the fail-safe fallback: tool calls
  that match no permission rule prompt instead of auto-running. Pair it with
  `../permissions/grok-config.permissions.toml` and, optionally, a relay hook.
- **`[projects.'<your-project-path>'] / trust_level`** — auto-trust specific
  directories so Grok doesn't re-prompt each session. Substitute your own
  paths; add one block per trusted project.

## Adding your own hooks and paths

These templates deliberately omit hooks tied to specific plugins,
episodic-memory tooling, approval relays, or other external tools — those
are yours to add. When you do, keep paths generic in anything you commit
to a shared repo, and keep machine-specific absolute paths in your live
local config only.
