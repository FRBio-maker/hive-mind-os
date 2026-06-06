"""Session-start hook: build and print the wiki manifest to stdout.

Designed to be wired into a runtime's SessionStart hook so the manifest
is injected into the agent's context automatically at the start of each
session. The manifest is the Layer-1 navigation backbone — a compact list
of every topic hub and its TL;DR.

The agent reads this once at session start, then uses semantic association
to decide which hubs to walk deeper into on demand.

Vault-root resolution (same priority order as sibling scripts):
  1. --root CLI argument
  2. WIKI_ROOT environment variable
  3. Current working directory

Usage:
    python session_start_hook.py --root <path-to-vault>
    WIKI_ROOT=<path-to-vault> python session_start_hook.py
    python session_start_hook.py          # defaults to current dir

The manifest is printed to stdout (for the runtime to inject) and also
written to <vault>/MANIFEST.md (for human browsing and manual reads).

Exit codes:
    0 — manifest built and printed successfully
    1 — no topics/ directory found under the vault root
"""

import argparse
import sys
from pathlib import Path

# Import build_manifest and resolve_root from the sibling gen_manifest
# module so there is a single source of truth for manifest generation.
# Both files live in the same scripts/ directory; the import works when
# this script is run from that directory or via `python -m` with the
# directory on sys.path.
try:
    from gen_manifest import build_manifest, resolve_root
except ImportError:
    # Fallback: add the directory this file lives in to sys.path, then retry.
    sys.path.insert(0, str(Path(__file__).parent))
    from gen_manifest import build_manifest, resolve_root


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="session_start_hook",
        description=(
            "Build the wiki manifest and print it to stdout for "
            "SessionStart context injection."
        ),
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Vault root (default: WIKI_ROOT env var, else current dir).",
    )
    args = parser.parse_args(argv)

    root = resolve_root(args.root)
    topics = root / "topics"
    if not topics.is_dir():
        print(
            f"ERROR: {topics} does not exist — "
            "no topics/ directory found under the vault root.",
            file=sys.stderr,
        )
        return 1

    manifest = build_manifest(root=root)

    # Write to MANIFEST.md so the file stays current for manual reads.
    out = root / "MANIFEST.md"
    out.write_text(manifest, encoding="utf-8")

    # Reconfigure stdout to UTF-8 before printing, so hub TL;DRs with
    # non-ASCII characters don't crash on Windows consoles that default
    # to a legacy codepage.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    # Print to stdout — this is what the SessionStart hook captures and
    # injects into the agent's context.
    sys.stdout.write(manifest)

    print(f"\n# wrote manifest to {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
