"""Edge-rel guard: reject any edge whose `rel:` is outside SCHEMA.md §5.

Single responsibility — this is NOT the source-binding classifier (that's
lint_binding.py). This walks every node and fails (exit 1) if any edge uses a
relationship name outside the closed set of 9 valid types. It exists because
hand-authored edges drift off-schema over time (continues, contains, ...);
wired into the vault's git pre-commit hook, it stops that drift at commit time.

Checks BOTH layers an edge lives in:
  1. frontmatter `edges:` block  — the canonical machine-parseable rel
  2. `## Connections` list items  — `- [[t]] *(rel, w=N)*` annotations, because
     any Connections-to-frontmatter sync pass copies a Connections annotation
     rel straight into frontmatter without validating it, so a bad annotation
     can silently become a bad frontmatter edge.

Deliberately ignores `_templates/` (the node template literally documents the
`*(rel, w=0.X)*` placeholder) and prose mentions (only true `- [[...]]` list
items are checked), so doc examples don't false-positive.

Vault-root resolution: --vault-root flag > WIKI_ROOT environment variable >
current directory. Nothing is hardcoded to a personal vault path.

Exit code: 0 = clean, 1 = off-schema rel(s) found (offenders printed).

Usage:
    python scripts/lint_edges.py                      # scan whole vault
    python scripts/lint_edges.py --vault-root <path>  # scan another vault
    python scripts/lint_edges.py nodes/a.md topics/b.md   # scan given files
                                  # (pre-commit passes the staged .md files
                                  # here so it gates what's being committed,
                                  # not unrelated WIP)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from gen_manifest import resolve_root
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from gen_manifest import resolve_root

# SCHEMA.md §5 — the closed set. Keep in sync with the schema table.
VALID = {
    "supports", "contradicts", "depends_on", "derived_from",
    "related_to", "part_of", "preceded_by", "followed_by", "authored_by",
}

FM = "---"
FM_REL = re.compile(r"^\s*rel:\s*[\"']?([A-Za-z_\-]+)[\"']?\s*$")
# a Connections LIST ITEM with an annotation; prose mentions don't start with "- [["
CONN_ITEM = re.compile(r"^\s*-\s*\[\[[^\]]+\]\].*?\*\(\s*([a-z_]+)\s*,\s*w\s*=")


def split_frontmatter(text: str):
    """Return (fm_lines, body_lines) or None if there's no frontmatter block."""
    if not text.startswith(FM + "\n"):
        return None
    lines = text.split("\n")
    close = next((i for i in range(1, len(lines)) if lines[i].strip() == FM), None)
    if close is None:
        return None
    return lines[1:close], lines[close + 1:]


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_no, layer, rel) offenders for one file."""
    try:
        # utf-8-sig: files written by PowerShell can carry a UTF-8 BOM that
        # would otherwise break the frontmatter-open match on line 1.
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return []
    parts = split_frontmatter(text)
    if parts is None:
        return []
    fm_lines, body_lines = parts
    offenders: list[tuple[int, str, str]] = []
    # frontmatter edges (line numbers are 1-based, +2 accounts for the opening ---)
    for i, ln in enumerate(fm_lines):
        m = FM_REL.match(ln)
        if m and m.group(1) not in VALID:
            offenders.append((i + 2, "frontmatter", m.group(1)))
    # connections list-item annotations (body starts after the closing ---)
    body_start = len(fm_lines) + 2  # line number where body begins
    for i, ln in enumerate(body_lines):
        m = CONN_ITEM.match(ln)
        if m and m.group(1) not in VALID:
            offenders.append((body_start + i + 1, "connections", m.group(1)))
    return offenders


def iter_nodes(vault: Path):
    """All node markdown files (nodes/, topics/, sources/), excluding _templates/."""
    for sub in ("nodes", "topics", "sources"):
        d = vault / sub
        if not d.exists():
            continue
        for f in d.rglob("*.md"):
            if "_templates" in f.parts:
                continue
            yield f


def select_files(vault: Path, paths: list[str]) -> list[Path]:
    """Files to scan: the given paths if any (resolved against vault, _templates
    and non-.md skipped), else a full walk of nodes/topics/sources."""
    if not paths:
        return sorted(iter_nodes(vault))
    out = []
    for raw in paths:
        f = Path(raw)
        if not f.is_absolute():
            f = vault / raw
        if f.suffix == ".md" and "_templates" not in f.parts and f.exists():
            out.append(f)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lint_edges")
    p.add_argument(
        "--vault-root",
        default=None,
        help="Vault root (default: WIKI_ROOT env var, else current dir).",
    )
    p.add_argument("paths", nargs="*",
                   help="specific files to scan (default: whole vault). The "
                        "pre-commit hook passes the staged .md files here so it "
                        "gates what's being committed, not unrelated WIP.")
    args = p.parse_args(argv)

    vault = resolve_root(args.vault_root)
    total = 0
    bad_files = 0
    for f in select_files(vault, args.paths):
        offenders = scan_file(f)
        if offenders:
            bad_files += 1
            try:
                rel_path = f.relative_to(vault).as_posix()
            except ValueError:
                rel_path = f.as_posix()
            for line_no, layer, rel in offenders:
                total += 1
                print(f"  {rel_path}:{line_no} [{layer}] off-schema rel: '{rel}'")

    if total:
        print(f"\nFAIL: {total} off-schema edge rel(s) across {bad_files} file(s).")
        print(f"Valid rels (SCHEMA.md §5): {', '.join(sorted(VALID))}")
        return 1
    print("OK: all edge rels conform to SCHEMA.md §5.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
