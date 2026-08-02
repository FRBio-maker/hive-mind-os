# skills/

Sanitized, template-grade ports of the skills that make the hive-mind's core
moves runnable: `consult` (cross-vendor decision review), `council` (internal
four-voice dissent), `delegate-external` (cross-vendor worker dispatch), and
`browser-ops` (fleet browser hands-and-eyes). Each `SKILL.md` carries a
template note listing what an adopter must localize — mostly your
`routing.toml` roster and knowledge-base paths. On the reference fleet, skills
live where the runtime loads them (`~/.claude/skills/`) and that directory is
its own versioned git repo, so skill evolution has history without any symlink
indirection. Not everything belongs in public: these four are published because
they are doctrine — the fleet's operating protocol; personal and domain skills
(private workflows, employer/domain specifics, anything referencing your own
infra or data) stay in your private skills repo.
