"""Tests for lint_edges.py — the closed-set edge-vocabulary guard.

Covers both layers (frontmatter `rel:` and `## Connections` annotations),
the _templates/ exemption, and staged-paths mode (pre-commit usage).
"""

from lint_edges import main


GOOD_NODE = (
    "---\n"
    "type: note\n"
    "edges:\n"
    "  - to: \"topics/alpha\"\n"
    "    rel: related_to\n"
    "    weight: 0.5\n"
    "---\n\n"
    "# Good\n\n"
    "## Connections\n"
    "- [[topics/alpha]] *(related_to, w=0.5)* — fine\n"
)

BAD_FRONTMATTER_NODE = (
    "---\n"
    "type: note\n"
    "edges:\n"
    "  - to: \"topics/alpha\"\n"
    "    rel: continues\n"
    "    weight: 0.5\n"
    "---\n\n"
    "# Bad\n"
)

BAD_CONNECTIONS_NODE = (
    "---\n"
    "type: note\n"
    "---\n\n"
    "# Bad\n\n"
    "## Connections\n"
    "- [[topics/alpha]] *(contains, w=0.8)* — off-schema annotation\n"
)


def _vault(tmp_path):
    (tmp_path / "nodes").mkdir()
    return tmp_path


def test_clean_vault_passes(tmp_path, capsys):
    vault = _vault(tmp_path)
    (vault / "nodes" / "good.md").write_text(GOOD_NODE, encoding="utf-8")
    assert main(["--vault-root", str(vault)]) == 0
    assert "OK" in capsys.readouterr().out


def test_off_schema_frontmatter_rel_fails(tmp_path, capsys):
    vault = _vault(tmp_path)
    (vault / "nodes" / "bad.md").write_text(BAD_FRONTMATTER_NODE, encoding="utf-8")
    assert main(["--vault-root", str(vault)]) == 1
    out = capsys.readouterr().out
    assert "continues" in out and "[frontmatter]" in out
    # The failure message reminds the author of the valid closed set.
    assert "related_to" in out


def test_off_schema_connections_annotation_fails(tmp_path, capsys):
    vault = _vault(tmp_path)
    (vault / "nodes" / "bad.md").write_text(BAD_CONNECTIONS_NODE, encoding="utf-8")
    assert main(["--vault-root", str(vault)]) == 1
    out = capsys.readouterr().out
    assert "contains" in out and "[connections]" in out


def test_templates_are_ignored(tmp_path):
    """The node template documents the *(rel, w=0.X)* placeholder — no false positive."""
    vault = _vault(tmp_path)
    tpl_dir = vault / "nodes" / "_templates"
    tpl_dir.mkdir()
    (tpl_dir / "node-template.md").write_text(BAD_FRONTMATTER_NODE, encoding="utf-8")
    assert main(["--vault-root", str(vault)]) == 0


def test_staged_paths_mode_scans_only_given_files(tmp_path):
    """Pre-commit passes staged paths: unrelated WIP must not gate the commit."""
    vault = _vault(tmp_path)
    (vault / "nodes" / "good.md").write_text(GOOD_NODE, encoding="utf-8")
    (vault / "nodes" / "bad.md").write_text(BAD_FRONTMATTER_NODE, encoding="utf-8")
    # Only the good file is staged -> clean.
    assert main(["--vault-root", str(vault), "nodes/good.md"]) == 0
    # Staging the bad file -> fail.
    assert main(["--vault-root", str(vault), "nodes/bad.md"]) == 1
