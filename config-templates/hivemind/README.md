# hivemind/ — the role-slot control plane (templates)

Starter copies of the three files that make roles *slots* instead of fixed
identities. Full doctrine: [`docs/playbooks/README.md`](../../docs/playbooks/README.md).

| File | Install at | What it is |
|---|---|---|
| `roles.toml` | shared fleet state, e.g. `<tooling-repo>/shared/hivemind/roles.toml` | Who holds the CEO and orchestrator slots, and the worker pool |
| `mode.state` | beside `roles.toml` | One word — `present` (orchestrator apex, human in loop) or `away` (CEO apex, unsupervised) |
| `routing.toml` | the **orchestrator runtime's** config dir (reference deployment: `~/.claude/routing.toml`) | Task-class → worker routing table; picks *within* the pool `roles.toml` defines |

**`mode.state` format note:** the file admits **no comments and no extra
lines** — the resolver reads the whole file, strips whitespace, and
lowercases; any content other than exactly `present` or `away` degrades to
`present` (the safe, human-in-the-loop default). Keep it a single word. That
is also why the explanation lives here in this README rather than in the file
itself.

**Resolver contract** (reference implementation is a small script beside the
live files): it never raises — a malformed or missing `roles.toml` degrades to
the safe default (orchestrator = `claude`, everyone else = worker,
mode = `present`) rather than aborting session start for the whole fleet.

> ⚠️ `mode.state = away` (CEO apex, unsupervised) is **not** the relay's
> presence (AFK) toggle (`docs/human-in-the-loop.md`), which merely routes
> approval prompts to your phone instead of the terminal. Don't conflate them.
