# commands/

Slash commands are **runtime-loaded prompt templates**: when the user types
`/save`, the runtime injects the matching markdown file into the conversation
as the instruction for that turn (with `$ARGUMENTS` substituted). They contain
no code of their own — any shell steps they describe are executed by the agent
through its normal tools, which is why each file here separates the
**normative contract** (what the command must do) from the **reference
implementation** (how the reference fleet happens to do it).

**Install location.** On the reference fleet the canonical copies live in
`<tooling-repo>/shared/claude-commands/` (so they're versioned with the rest
of the agent tooling) and are symlinked into `~/.claude/commands/`, where the
runtime discovers them. Adopters can skip the indirection and just copy these
files into `~/.claude/commands/` — the symlink only matters if you want one
versioned source of truth across machines.

**What ships here:**

| Command | Purpose |
|---|---|
| `save.md` | End-of-session checkpoint: finalize wiki cluster → reconcile hub state → pending rollup → manifest regen → binding lint → commit + push |
| `quicksave.md` | Mid-session wiki flush (subset of /save, no git); auto-fires at ~30% remaining context; writes a resume-grade handoff |
| `afk.md` | Force the phone relay ON (sticky) via the four-flag contract |
| `back.md` | Clear all four relay flags → back to idle-gated default |

**Note on `/council`:** there is no separate council command logic — on the
reference fleet `/council` is a thin trigger file that simply invokes the
`council` skill (see `skills/council/`) on `$ARGUMENTS`. If your runtime can
trigger skills by name, a one-line command file that says "run the council
skill on $ARGUMENTS" is all you need. `/consult` works the same way against
`skills/consult/`.

Every file carries a template-note comment listing what to localize (vault
paths, presence-flag locations, venv invocation).
