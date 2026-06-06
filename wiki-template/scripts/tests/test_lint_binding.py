"""Tests for lint_binding.py.

Verifies that lint() returns 0 when all clusters are bound to a topic hub
and 1 when any cluster is missing the required related_to edge.

Setup mirrors test_binding.py — a minimal tmp vault is constructed
directly in the test without touching any live vault.
"""

from pathlib import Path

import pytest


def _write_summary(cluster_dir: Path, bound: bool) -> None:
    """Write a _summary.md into cluster_dir, bound or unbound."""
    cluster_dir.mkdir(parents=True, exist_ok=True)
    if bound:
        content = (
            "---\n"
            "edges:\n"
            "  - to: topics/agent-protocols\n"
            "    rel: related_to\n"
            "    weight: 0.8\n"
            "---\n"
            "# Bound cluster\n"
        )
    else:
        content = (
            "---\n"
            "edges: []\n"
            "---\n"
            "# Unbound cluster\n"
        )
    (cluster_dir / "_summary.md").write_text(content, encoding="utf-8")


def test_lint_returns_zero_when_all_bound(tmp_path):
    """lint() returns 0 when every cluster has a related_to edge."""
    from lint_binding import lint

    nodes = tmp_path / "nodes"
    _write_summary(nodes / "2024-01-01-alpha", bound=True)
    _write_summary(nodes / "2024-01-02-beta", bound=True)

    assert lint(root=tmp_path) == 0


def test_lint_returns_one_when_unbound_cluster_exists(tmp_path):
    """lint() returns 1 when at least one cluster is missing a related_to edge."""
    from lint_binding import lint

    nodes = tmp_path / "nodes"
    _write_summary(nodes / "2024-01-01-bound", bound=True)
    _write_summary(nodes / "2024-01-02-unbound", bound=False)

    assert lint(root=tmp_path) == 1


def test_lint_returns_zero_for_empty_nodes_dir(tmp_path):
    """lint() returns 0 when nodes/ exists but is empty (nothing to check)."""
    from lint_binding import lint

    (tmp_path / "nodes").mkdir()

    assert lint(root=tmp_path) == 0


def test_lint_returns_zero_when_no_nodes_dir(tmp_path):
    """lint() returns 0 when there are no clusters at all."""
    from lint_binding import lint

    assert lint(root=tmp_path) == 0
