# Repo Map — file structure & the logic it drives

> **TL;DR (≤80 words):** A map of what is *actually in this repository* and how
> each file drives behavior. `INFRASTRUCTURE.md` diagrams the **deployed system**
> (four repos, companions, the running fleet). This document is narrower and more
> literal: the shipped file tree, the boundary between what ships here and what
> you bring yourself, the bootstrap install/rollback state machine, and the
> session-start data flow through the shipped wiki scripts. Read this to
> understand the box; read `INFRASTRUCTURE.md` to understand the machine the box
> joins.

---

## 1. The shipped file tree (annotated)

Every path below is tracked in this repo. Roles are grouped by the four concerns
the doctrine separates: **RULES**, **KNOWLEDGE starter**, **INSTALL**, **DOCS**.

```
hive-mind-os/
│
├── README.md                 ← human entry point (install + philosophy)
├── ONBOARDING.md             ← agent entry point (pasted into a fresh agent)
├── CONTRIBUTING.md           ← contribution + sanitisation rules (public hygiene)
├── LICENSE                   ← MIT
│
├── identity/                 ── RULES: one doctrine file per runtime ───────────
│   ├── CLAUDE.md             ← Claude Code  → ~/.claude/CLAUDE.md
│   ├── AGENTS.md             ← Codex CLI    → ~/.codex/AGENTS.md
│   ├── GEMINI.md             ← Gemini CLI   → ~/.gemini/GEMINI.md
│   └── GROK.md               ← Grok         → ~/.grok/AGENTS.md  (Grok reads AGENTS.md)
│
├── permissions/              ── RULES: versioned permission *excerpts* (keys only)
│   ├── claude-settings.permissions.json
│   ├── codex-config.permissions.toml
│   ├── gemini-settings.permissions.json
│   ├── gemini-policies/claude-mirror.toml
│   ├── grok-config.permissions.toml
│   └── README.md             ← how to MERGE excerpts into a live settings file
│
├── config-templates/         ── RULES: starter configs (full files, not excerpts)
│   ├── claude/settings.json
│   ├── codex/config.toml
│   ├── gemini/settings.json
│   ├── grok/config.toml
│   └── README.md
│
├── bootstrap/                ── INSTALL: wire identity files into runtime dirs ──
│   ├── bootstrap.py          ← cross-platform installer (dry-run default; the
│   │                            symlink/copy + backup + rollback state machine)
│   ├── setup-macos.sh        ← per-OS entry point (macOS; landmine notes in header)
│   ├── setup-linux.sh        ← per-OS entry point (Linux/WSL)
│   ├── setup-windows.ps1     ← per-OS entry point (Windows)
│   └── test_bootstrap.py     ← pytest suite for the installer
│
├── wiki-template/            ── KNOWLEDGE starter: a vault you can scaffold ─────
│   ├── SCHEMA.md             ← the node/edge/traversal protocol (canonical)
│   ├── README.md
│   ├── _templates/           ← node / cluster / session / project-wiki templates
│   └── scripts/              ← the SHIPPED wiki toolkit (+ its own tests)
│       ├── scaffold.py             ← create a fresh vault from the template
│       ├── gen_manifest.py         ← write MANIFEST.md (title-only hub list)
│       ├── bind_clusters.py        ← write BINDING_QUEUE.md (orphan clusters)
│       ├── lint_binding.py         ← CI gate: every cluster must bind to a hub
│       ├── session_start_hook.py   ← inject MANIFEST + BINDING_QUEUE at start
│       ├── requirements.txt
│       └── tests/                  ← pytest suites for the above
│
└── docs/                     ── DOCS: the protocol, deeper than the identity files
    ├── INFRASTRUCTURE.md     ← the deployed-system view (7 Mermaid diagrams)
    ├── memory-architecture.md
    ├── permissions-protocol.md
    ├── wiki-protocol.md
    ├── human-in-the-loop.md  ← relay pattern (the relay itself is NOT shipped)
    ├── hygiene.md            ← shipped vs documented-add-on wiki hygiene
    └── multi-runtime.md      ← cross-runtime parity + divergences
```

**The one structural rule:** `identity/` and `config-templates/` hold *full files*
the installer places; `permissions/` holds *excerpts* (permission keys only) that
get **merged** into a live settings file so machine-specific keys (MCP servers,
plugin marketplaces) survive. Symlink the doctrine; merge the permissions.

---

## 2. What ships here vs. what you bring

The doctrine names four concerns. This repo ships two of them outright (RULES +
a KNOWLEDGE starter) and documents the other two as **companions you bring or
build**. This boundary is the single most important thing to understand before
adopting.

```mermaid
flowchart TB
    subgraph SHIP["✅ SHIPPED in this repo"]
        direction TB
        R["RULES<br/>identity/ · permissions/ · config-templates/ · docs/"]
        K["KNOWLEDGE starter<br/>wiki-template/ (SCHEMA + scaffold + manifest + lint)"]
        I["INSTALL<br/>bootstrap/ (symlink · backup · rollback)"]
    end

    subgraph BYO["🔌 COMPANION — bring or build your own"]
        direction TB
        T["EXECUTABLES (tooling repo)<br/>hooks · delegate-* bins · routing.toml · shared skills"]
        H["HUMAN-IN-THE-LOOP (approval-relay)<br/>daemon · adapters · mailbox<br/>pattern → docs/human-in-the-loop.md"]
        E["EPISODIC capture layer<br/>e.g. claude-mem (PostToolUse/Stop hooks)"]
        C["WORKING-MEMORY<br/>e.g. context-mode MCP (output containment)"]
    end

    R -. "session-start hook calls" .-> K
    I -. "places" .-> R
    R -. "ASK rules escalate to" .-> H
    R -. "delegate-external routes via" .-> T
    R -. "cued retrieval from" .-> E
    R -. "offloads large output to" .-> C

    classDef ship fill:#dfd,stroke:#393,stroke-width:2px
    classDef byo fill:#eef,stroke:#669,stroke-dasharray:4 3
    class R,K,I ship
    class T,H,E,C byo
```

**Why the split:** RULES and KNOWLEDGE are plain text — portable, auditable, no
runtime dependency. The companions are *deployable code with their own lifecycles*
(a daemon, a hook runner, an MCP server). Shipping them would couple the template
to one stack; documenting their *contracts* lets an adopter wire any equivalent.

> The seams are contracts, not imports. The session hook needs a script-runner
> (`session_start_hook.py` is the reference). The relay needs a command that
> takes `--prompt` and writes the human's reply to stdout. Meet the contract with
> whatever you already run.

---

## 3. Bootstrap logic — the install/rollback state machine

`bootstrap.py` is deliberately paranoid: it is **dry-run by default**, it **never
overwrites without a backup**, and `--rollback` **can never delete a file it
didn't create**. This diagram is the actual control flow.

```mermaid
flowchart TD
    Start([python bootstrap.py ...])
    Start --> Mode{flag?}

    Mode -->|no flag| Plan["plan_actions()<br/>print dry-run plan<br/>WRITE NOTHING"]
    Mode -->|--rollback| RB

    Mode -->|--apply| Apply
    Apply --> Each{for each<br/>identity file}
    Each -->|dest exists,<br/>no --force| Skip["SKIP<br/>(use --force to replace)"]
    Each -->|dest free, or --force| Backup["if dest exists →<br/>move to dest.bak.&lt;timestamp&gt;"]
    Backup --> Link{os.symlink}
    Link -->|ok| Linked["LINK ✓<br/>(write-through: repo edits go live)"]
    Link -->|OSError<br/>no symlink priv| Copy{shutil.copy2}
    Copy -->|ok| Copied["COPY ⚠<br/>(no live propagation —<br/>enable Developer Mode)"]
    Copy -->|also fails| Restore["RESTORE backup → dest<br/>(transactional: never leave dest empty)<br/>then raise"]

    RB --> RBEach{for each<br/>identity file}
    RBEach -->|backup exists| RBrestore["REMOVE dest →<br/>RESTORE newest .bak"]
    RBEach -->|no backup,<br/>symlink INTO this repo| RBremove["REMOVE<br/>(proven ours)"]
    RBEach -->|no backup,<br/>real file or foreign symlink| RBskip["SKIP — leave untouched<br/>(never destroy a file we didn't install)"]

    classDef safe fill:#dfd,stroke:#393
    classDef warn fill:#ffe,stroke:#a83
    classDef danger fill:#fdd,stroke:#a33
    class Plan,Linked,RBrestore,RBremove,RBskip safe
    class Copied,Skip,Backup warn
    class Restore danger
```

**Install mapping** (`_mappings`):

| Source (this repo) | Destination (runtime) | Note |
|---|---|---|
| `identity/CLAUDE.md` | `~/.claude/CLAUDE.md` | |
| `identity/AGENTS.md` | `~/.codex/AGENTS.md`  | |
| `identity/GEMINI.md` | `~/.gemini/GEMINI.md` | |
| `identity/GROK.md`   | `~/.grok/AGENTS.md`   | Grok loads `AGENTS.md`, never `GROK.md` |

The ownership test (`_is_symlink_into_repo`) is what makes `--rollback` safe: it
resolves the link target and only reclaims a dest whose link points *inside* this
repo. A hand-written file, or a symlink you made pointing elsewhere, is left
alone.

---

## 4. Session-start data flow — the shipped wiki loop

What the KNOWLEDGE half does at the start of every session. Only the **manifest**
(Layer-1 hub titles) is injected; deeper layers are walked on demand per the Wiki
Protocol. This is the whole shipped feedback loop — no LLM, no network.

```mermaid
flowchart LR
    Vault[("vault/<br/>topics/ · nodes/ · sources/")]

    subgraph SCRIPTS["wiki-template/scripts/ (shipped)"]
        GEN["gen_manifest.py"]
        BIND["bind_clusters.py"]
        HOOK["session_start_hook.py"]
        LINT["lint_binding.py"]
    end

    Vault --> GEN --> MAN["MANIFEST.md<br/>(title-only hub list)"]
    Vault --> BIND --> BQ["BINDING_QUEUE.md<br/>(clusters with no topic edge)"]
    MAN --> HOOK
    BQ --> HOOK
    HOOK -->|"additionalContext<br/>at session start"| AGENT["Agent context<br/>(attention window)"]

    AGENT -->|"on each message:<br/>scan → walk hub if hit"| Vault
    AGENT -->|"session end:<br/>bind cluster → topic"| Vault
    Vault --> LINT -->|"exit ≠ 0 if any<br/>cluster unbound"| CI([CI / pre-commit gate])

    classDef store fill:#dfe9f3,stroke:#369
    classDef gen fill:#dfd,stroke:#393
    class Vault,MAN,BQ store
    class GEN,BIND,HOOK,LINT gen
```

**Documented but NOT shipped** (see `docs/hygiene.md`): the per-hub `Current
truth` block reconciler and the local-LLM contradiction judge. They are described
as input-contracts so you can wire your own; the template enforces only the one
CI-safe rule — *every cluster binds to a topic hub* (`lint_binding.py`).

---

## 5. Shipped / documented-only / companion — the honest inventory

| Capability | Status | Where |
|---|---|---|
| Identity doctrine (4 runtimes) | **shipped** | `identity/` |
| Permission excerpts + merge guide | **shipped** | `permissions/` |
| Config starters | **shipped** | `config-templates/` |
| Installer (symlink/copy/backup/rollback) | **shipped** | `bootstrap/` |
| Wiki schema + scaffold | **shipped** | `wiki-template/` |
| Manifest + binding queue + binding lint | **shipped** | `wiki-template/scripts/` |
| Session-start manifest injection | **shipped** (reference impl) | `session_start_hook.py` |
| Per-hub truth blocks | documented add-on | `docs/hygiene.md` |
| Contradiction judge (local LLM) | documented add-on | `docs/hygiene.md` |
| Source-library ingest (PDF → sidecars) | **not included** | `SCHEMA.md §7` describes the workflow; bring your own ingest step |
| Delegation routing (`routing.toml`, wrappers) | companion | tooling repo (`docs/INFRASTRUCTURE.md` §6) |
| Hooks / custom bins / shared skills | companion | tooling repo |
| Approval relay (daemon + adapters) | companion | `docs/human-in-the-loop.md` |
| Episodic capture (e.g. claude-mem) | companion | `docs/memory-architecture.md` |
| Working-memory (e.g. context-mode) | companion | `docs/memory-architecture.md` |

---

## 6. The three rules, restated against this tree

1. **Symlink discipline** — `bootstrap/` makes every runtime identity file a
   symlink into `identity/`. One source of truth; `git pull` propagates.
2. **Permission discipline** — every tool call hits the resolver seeded from
   `permissions/`. Allow and hard-deny are silent; ASK escalates to the
   (companion) relay; timeout defaults to deny.
3. **Memory discipline** — identity always loaded; `wiki-template/` manifest
   injected at Layer 1; deeper layers walked on demand; episodic + working
   memory are cued/transient companions.

Two concerns ship, two you bring. The seams between them are written contracts,
not code dependencies — which is why the doctrine survives swapping any one
component out.
