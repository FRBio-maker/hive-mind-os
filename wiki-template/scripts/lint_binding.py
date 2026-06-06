"""CI gate for wiki binding hygiene.

Exits non-zero when any session cluster is unbound — i.e. its `_summary.md`
carries no `related_to` edge to a `topics/` hub. Wire this into a pre-commit
hook or CI step to keep the graph from drifting into a pile of orphaned
clusters.

Vault-agnostic: the vault root comes from the --root argument, the WIKI_ROOT
environment variable, or the current directory (in that order). Nothing is
hardcoded to a personal vault path.

The unbound-detection logic is shared with bind_clusters.py (single source of
truth for "what counts as bound"); this module just turns the result into an
exit code and a human-readable report.

Usage:
    python scripts/lint_binding.py --root <vault>
    WIKI_ROOT=<vault> python scripts/lint_binding.py

Exit codes:
    0 — every cluster is bound (or there are no clusters)
    1 — one or more unbound clusters exist
"""

import argparse
import sys

from bind_clusters import find_unbound, resolve_root


def lint(root=None) -> int:
    """Return 0 if all clusters are bound, 1 if any are unbound.

    Prints a short report to stdout as a side effect so the same call works
    as both a library check and a CLI gate.
    """
    root = resolve_root(root)
    unbound = find_unbound(root)
    if not unbound:
        print("Binding lint: OK — all clusters bound to a topic hub.")
        return 0
    print(f"Binding lint: FAIL — {len(unbound)} unbound cluster(s):")
    for cluster_dir in unbound:
        print(f"  - {cluster_dir.name}")
    print("Run bind_clusters.py for the full queue, then add a "
          "`related_to topics/<hub>` edge to each _summary.md.")
    return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="lint_binding",
        description="Exit non-zero when unbound session clusters exist.",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="Vault root (default: WIKI_ROOT env var, else current dir).",
    )
    args = parser.parse_args(argv)
    return lint(root=args.root)


if __name__ == "__main__":
    sys.exit(main())
