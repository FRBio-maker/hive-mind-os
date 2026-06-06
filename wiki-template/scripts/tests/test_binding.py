def test_find_unbound(tmp_path):
    nodes = tmp_path / "nodes"
    (nodes / "bound").mkdir(parents=True)
    (nodes / "unbound").mkdir(parents=True)
    (nodes / "bound" / "_summary.md").write_text(
        "---\nedges:\n  - to: topics/x\n    rel: related_to\n---\n# Bound\n", encoding="utf-8")
    (nodes / "unbound" / "_summary.md").write_text("---\nedges: []\n---\n# Unbound\n", encoding="utf-8")
    from bind_clusters import find_unbound
    assert [c.name for c in find_unbound(root=tmp_path)] == ["unbound"]


def test_lint_exit_codes(tmp_path):
    """lint() returns non-zero when unbound clusters exist, zero otherwise."""
    from bind_clusters import find_unbound  # noqa: F401 — ensures module imports
    from lint_binding import lint
    nodes = tmp_path / "nodes"
    (nodes / "unbound").mkdir(parents=True)
    (nodes / "unbound" / "_summary.md").write_text(
        "---\nedges: []\n---\n# Unbound\n", encoding="utf-8")
    assert lint(root=tmp_path) != 0

    (nodes / "unbound" / "_summary.md").write_text(
        "---\nedges:\n  - to: topics/x\n    rel: related_to\n---\n# Now bound\n",
        encoding="utf-8")
    assert lint(root=tmp_path) == 0
