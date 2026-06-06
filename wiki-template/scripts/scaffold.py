"""Scaffold session clusters and fresh vaults.

Two jobs:

1. `new_cluster(root, slug, date)` — create a session cluster at
   `<root>/nodes/<date>-<slug>/_summary.md` from the `_templates/cluster.md`
   template, substituting the date and slug. This is the Doer-mode session
   start (SCHEMA.md §9) reduced to one command.

2. `init_vault(root)` — lay down a fresh vault skeleton: `topics/`, `nodes/`,
   `_templates/`, and a copy of `SCHEMA.md`. Use this once when starting a new
   vault from the template.

Vault-agnostic: the root comes from --root / WIKI_ROOT / current dir for the
cluster command, and from --vault for the init command. Nothing is hardcoded
to a personal vault path.

The template and SCHEMA sources are located relative to THIS file (the
`wiki-template/` package root is the script's grandparent), so the commands
work regardless of the current working directory. If a template is missing,
a built-in fallback is used so the tool degrades gracefully rather than
crashing.

Usage:
    # new session cluster (date defaults to today)
    python scripts/scaffold.py --slug my-thing --root <vault>
    python scripts/scaffold.py --slug my-thing --date 2026-06-06

    # initialize a fresh vault skeleton
    python scripts/scaffold.py --vault <path-to-new-vault>
"""

import argparse
import os
import shutil
import sys
from datetime import date as _date
from pathlib import Path

# wiki-template/ root = this file's grandparent (scripts/ -> wiki-template/).
TEMPLATE_ROOT = Path(__file__).resolve().parent.parent
CLUSTER_TEMPLATE = TEMPLATE_ROOT / "_templates" / "cluster.md"
SCHEMA_SOURCE = TEMPLATE_ROOT / "SCHEMA.md"
TEMPLATES_SOURCE = TEMPLATE_ROOT / "_templates"

# Fallback used only if _templates/cluster.md is missing. Keeps the tool
# working even in a stripped-down checkout.
FALLBACK_CLUSTER = (
    "---\n"
    "type: session\n"
    "tags: []\n"
    "created: {date}\n"
    "status: draft\n"
    "session_id: {slug}\n"
    "edges: []\n"
    "---\n\n"
    "# Session {date} — {slug}\n\n"
    "> **TL;DR (≤80 words):** in progress\n\n"
    "## Connections\n\n"
    "## Detail\n"
)


def resolve_root(root=None) -> Path:
    """Resolve the vault root: explicit arg > WIKI_ROOT env > current dir."""
    if root is not None:
        return Path(root)
    env = os.environ.get("WIKI_ROOT")
    if env:
        return Path(env)
    return Path(".")


def _load_cluster_template() -> str:
    """Return the cluster template text, falling back to a built-in if missing."""
    try:
        return CLUSTER_TEMPLATE.read_text(encoding="utf-8")
    except OSError:
        return FALLBACK_CLUSTER


def new_cluster(root=None, slug="untitled", date=None) -> Path:
    """Create a session cluster <root>/nodes/<date>-<slug>/ and its _summary.md.

    Returns the cluster directory Path. Idempotent on the directory (won't
    clobber an existing _summary.md — raises if it already exists, so an
    accidental re-run doesn't silently overwrite session work).
    """
    root = resolve_root(root)
    if date is None:
        date = _date.today().isoformat()

    cluster_dir = root / "nodes" / f"{date}-{slug}"
    cluster_dir.mkdir(parents=True, exist_ok=True)

    summary = cluster_dir / "_summary.md"
    if summary.exists():
        raise FileExistsError(f"{summary} already exists — refusing to overwrite.")

    text = _load_cluster_template().replace("{date}", date).replace("{slug}", slug)
    summary.write_text(text, encoding="utf-8")
    return cluster_dir


def init_vault(root=None) -> Path:
    """Initialize a fresh vault skeleton at `root`.

    Creates topics/, nodes/, _templates/ and copies SCHEMA.md in. Existing
    files are left untouched (won't overwrite a SCHEMA.md you've customized).
    Returns the vault root Path.
    """
    root = resolve_root(root)
    root.mkdir(parents=True, exist_ok=True)

    for sub in ("topics", "nodes", "_templates"):
        (root / sub).mkdir(parents=True, exist_ok=True)

    # Copy SCHEMA.md (the protocol contract) if not already present.
    dest_schema = root / "SCHEMA.md"
    if not dest_schema.exists() and SCHEMA_SOURCE.exists():
        shutil.copyfile(SCHEMA_SOURCE, dest_schema)

    # Copy template files (node-template, session-summary, cluster, project-wiki).
    if TEMPLATES_SOURCE.is_dir():
        for item in TEMPLATES_SOURCE.iterdir():
            dest = root / "_templates" / item.name
            if dest.exists():
                continue
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copyfile(item, dest)

    return root


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="scaffold",
        description="Create a session cluster, or init a fresh vault skeleton.",
    )
    parser.add_argument(
        "--vault",
        default=None,
        help="Init a fresh vault skeleton at this path, then exit.",
    )
    parser.add_argument(
        "--slug",
        default=None,
        help="Session-cluster slug (creates nodes/<date>-<slug>/).",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Cluster date YYYY-MM-DD (default: today).",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Vault root for the cluster (default: WIKI_ROOT env, else cwd).",
    )
    args = parser.parse_args(argv)

    if args.vault:
        vault = init_vault(root=args.vault)
        print(f"Initialized vault skeleton at {vault}")
        return 0

    if args.slug:
        try:
            cluster = new_cluster(root=args.root, slug=args.slug, date=args.date)
        except FileExistsError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"Created cluster {cluster}")
        return 0

    parser.error("provide --vault to init a vault, or --slug to create a cluster")
    return 2


if __name__ == "__main__":
    sys.exit(main())
