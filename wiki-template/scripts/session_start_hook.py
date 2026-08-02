"""SessionStart hook: regenerate manifest + binding queue, inject into agent context.

This is the connective tissue between the agent's runtime and the Wiki
Manifest. On every session start, this script:
  1. Regenerates `MANIFEST.md` (Layer-1 navigation backbone, via
     `gen_manifest.py`)
  2. Regenerates `BINDING_QUEUE.md` (unbound clusters + promotion
     candidates, via `bind_clusters.py`)
  3. Regenerates `PENDING.md` — IF a hygiene rollup script exists (see
     below; the template does not ship one, so this step degrades
     gracefully to a no-op)
  4. Emits the manifest plus a <=10-line work-queue digest as
     `additionalContext` per the Claude Code SessionStart hook protocol
     (`hookSpecificOutput.additionalContext`).

IMPORTANT — output format. Claude Code SessionStart hooks must print a
JSON envelope on stdout; raw markdown on stdout is NOT injected into the
agent's context. The envelope shape:

    {
      "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "<markdown injected into context>"
      },
      "continue": true,
      "suppressOutput": true
    }

Failure isolation: if regeneration crashes, the script still emits a
valid JSON envelope (with empty/partial/stale content and an explicit
warning) so it never blocks session startup. If a previous MANIFEST.md
exists on disk but regeneration failed, the stale manifest is injected
anyway — stale beats nothing — behind an explicit STALE warning banner
so the agent doesn't navigate from an outdated map unknowingly. A crash
anywhere else produces a stub envelope carrying the traceback. Exit code
is always 0.

Vault-root resolution (same priority order as sibling scripts):
  1. --root CLI argument
  2. WIKI_ROOT environment variable
  3. Current working directory

Sibling scripts are invoked via subprocess with the same Python
interpreter (`sys.executable`, avoids "python not on PATH" surprises),
a 30s timeout each, and WIKI_ROOT set in the child environment so they
resolve the same vault root.

Wire into Claude Code via settings.json (adjust the path to where your
vault lives):

    "SessionStart": [
      { "hooks": [
          { "type": "command",
            "command": "python \"<vault>/scripts/session_start_hook.py\" --root \"<vault>\""
          }
      ]}
    ]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import traceback
from pathlib import Path

# Import resolve_root from the sibling gen_manifest module so there is a
# single source of truth for vault-root resolution. Both files live in the
# same scripts/ directory.
try:
    from gen_manifest import resolve_root
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from gen_manifest import resolve_root

# Sibling scripts always live next to this file (they ship together).
SCRIPTS_DIR = Path(__file__).resolve().parent
GEN_MANIFEST = SCRIPTS_DIR / "gen_manifest.py"
BIND_CLUSTERS = SCRIPTS_DIR / "bind_clusters.py"


def pending_generator(root: Path):
    """Locate an optional hygiene PENDING rollup script, or None.

    The template does not ship the hygiene suite; if you add one (a
    script that harvests `- [ ]` pending items from project hubs into
    `<vault>/PENDING.md`), drop it at either location below and the hook
    picks it up automatically. Missing script = soft skip, not an error.
    """
    candidates = [
        SCRIPTS_DIR / "hygiene" / "gen_pending.py",
        root / "scripts" / "hygiene" / "gen_pending.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def run_script(script_path: Path, root: Path) -> tuple:
    """Run a vault script. Return (success, error_msg).

    Uses sys.executable so we pick up the same Python the hook is
    running under. Captures stdout/stderr so they don't leak into the
    hook's JSON output. WIKI_ROOT is set in the child env so sibling
    scripts resolve the same vault root without needing CLI flags.
    """
    if script_path is None or not script_path.exists():
        return False, f"missing: {script_path}"
    env = dict(os.environ)
    env["WIKI_ROOT"] = str(root)
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if result.returncode != 0:
            return False, f"exit {result.returncode}: {result.stderr.strip()[:200]}"
        return True, ""
    except subprocess.TimeoutExpired:
        return False, f"timeout: {script_path.name}"
    except Exception as exc:  # noqa: BLE001 — isolation: never crash the hook
        return False, f"{type(exc).__name__}: {exc}"


def read_safe(path: Path) -> str:
    """Read a file. Empty string on any error — never raises."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def build_digest(queue_text: str, pending_text: str) -> list:
    """<=10-line digest replacing raw BINDING_QUEUE + PENDING dumps.

    PENDING.md format: bullets grouped under '## P1 ...' / '## P2 ...' /
    '## P3 ...' / '## Unprioritized ...' headings. BINDING_QUEUE.md: one
    '### `slug`' per unbound cluster. Any parse miss degrades to zero
    counts — never raises. Injecting a digest instead of the full files
    keeps session-start token cost flat as the queues grow.
    """
    section = None
    counts = {}
    p1_items = []
    for line in pending_text.splitlines():
        header = re.match(r"^## (\S+)", line)
        if header:
            section = header.group(1)
            counts[section] = 0
            continue
        if section and re.match(r"^\s*-\s+", line):
            counts[section] = counts.get(section, 0) + 1
            if section == "P1" and len(p1_items) < 3:
                p1_items.append(line.strip()[2:].strip())

    unbound = len(re.findall(r"^### ", queue_text, flags=re.M))

    lines = ["## Wiki work-queue digest"]
    if pending_text:
        total = sum(counts.values())
        breakdown = ", ".join(f"{k}: {v}" for k, v in counts.items()) or "none"
        lines.append(
            f"{total} open pending items ({breakdown}) | "
            f"{unbound} unbound clusters awaiting hub binding. "
            "Full lists on disk at the vault root: `PENDING.md`, "
            "`BINDING_QUEUE.md` — read on demand."
        )
        if p1_items:
            lines.append("Top P1 items:")
            for item in p1_items:
                lines.append(f"- {item[:200]}")
    else:
        # No PENDING.md (the hygiene rollup isn't wired) — queue-only digest.
        lines.append(
            f"{unbound} unbound clusters awaiting hub binding. "
            "Full list on disk at the vault root: `BINDING_QUEUE.md` — "
            "read on demand."
        )
    return lines


def build_context(root: Path) -> str:
    """Compose the additionalContext block from manifest + work-queue digest."""
    manifest_file = root / "MANIFEST.md"
    queue_file = root / "BINDING_QUEUE.md"
    pending_file = root / "PENDING.md"

    parts = []

    # Header — orient the agent on what these blocks are. Kept short: the
    # full Wiki Protocol lives in the agent's identity file; don't restate
    # it here.
    parts.append(
        "# Wiki state (auto-injected at session start by "
        "`scripts/session_start_hook.py`)"
    )
    parts.append("")
    parts.append(
        "Below: the **Wiki Manifest** (scan on every user message per the "
        "Wiki Protocol in your identity file) and a work-queue digest."
    )
    parts.append("")
    parts.append("---")
    parts.append("")

    # Regenerate + inject manifest.
    manifest_ok, manifest_err = run_script(GEN_MANIFEST, root)
    manifest_text = read_safe(manifest_file)
    if manifest_text:
        if not manifest_ok:
            # Regeneration failed but a previous manifest exists on disk.
            # Inject it anyway (stale beats nothing) but tell the agent,
            # so it doesn't navigate from an outdated map unknowingly.
            parts.append(
                f"> **WARNING: manifest regeneration failed "
                f"({manifest_err or 'unknown error'}) — the manifest below "
                f"is STALE (from a previous session).**"
            )
            parts.append("")
        parts.append(manifest_text.rstrip())
    else:
        parts.append("## Wiki Manifest (unavailable)")
        parts.append("")
        parts.append(f"`gen_manifest.py` failed: {manifest_err or 'no output'}")
    parts.append("")
    parts.append("---")
    parts.append("")

    # Regenerate the binding queue (and PENDING rollup, if a hygiene script
    # is wired) ON DISK, but inject only a <=10-line digest — full queue
    # dumps at every session start cost thousands of tokens for content the
    # agent rarely needs immediately.
    queue_ok, _ = run_script(BIND_CLUSTERS, root)
    gen_pending = pending_generator(root)
    if gen_pending is not None:
        pending_ok, _ = run_script(gen_pending, root)
    else:
        pending_ok = True  # not shipped -> soft skip, not an error
    parts.extend(build_digest(read_safe(queue_file), read_safe(pending_file)))
    if not (queue_ok and pending_ok):
        parts.append(
            "> (queue/pending regeneration had errors — digest may be stale)"
        )
    parts.append("")

    return "\n".join(parts)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="session_start_hook",
        description=(
            "Regenerate the wiki manifest + work queue and emit a "
            "SessionStart JSON envelope for context injection."
        ),
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Vault root (default: WIKI_ROOT env var, else current dir).",
    )
    args = parser.parse_args(argv)

    try:
        root = resolve_root(args.root)
        additional_context = build_context(root)
    except Exception:  # noqa: BLE001 — never crash session start
        # Emit a stub envelope with the error so the user knows something
        # is wrong but the session lives.
        additional_context = (
            "# Wiki state (session-start hook crashed)\n\n"
            "```\n" + traceback.format_exc() + "```\n"
        )

    envelope = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context,
        },
        "continue": True,
        "suppressOutput": True,
    }
    sys.stdout.write(json.dumps(envelope))
    return 0


if __name__ == "__main__":
    sys.exit(main())
