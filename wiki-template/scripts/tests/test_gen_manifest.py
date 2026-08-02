def test_manifest_lists_hubs(tmp_path):
    topics = tmp_path / "topics"; topics.mkdir()
    (topics / "alpha.md").write_text("---\ntype: topic\n---\n# Alpha\n> **TL;DR:** First hub.\n", encoding="utf-8")
    (topics / "beta.md").write_text("---\ntype: topic\n---\n# Beta\n> **TL;DR:** Second hub.\n", encoding="utf-8")
    from gen_manifest import build_manifest
    out = build_manifest(root=tmp_path)
    assert "alpha" in out and "First hub." in out
    assert "beta" in out and "Second hub." in out


def test_multiline_tldr_continuation_markers_stripped(tmp_path):
    """Continuation lines of a TL;DR blockquote carry '> ' prefixes that must
    not leak into the manifest as stray '>' characters mid-sentence."""
    topics = tmp_path / "topics"; topics.mkdir()
    (topics / "gamma.md").write_text(
        "# Gamma\n\n"
        "> **TL;DR:** First line of the summary\n"
        "> second line continues here.\n\n"
        "Detail.\n",
        encoding="utf-8",
    )
    from gen_manifest import build_manifest
    out = build_manifest(root=tmp_path)
    hub_line = next(ln for ln in out.splitlines() if "gamma" in ln)
    assert "second line continues" in hub_line
    assert ">" not in hub_line


def test_zero_hubs_is_an_error(tmp_path):
    """topics/ exists but holds no hubs -> exit 1, so the session-start hook
    falls back to the previous manifest instead of injecting a blank one."""
    (tmp_path / "topics").mkdir()
    from gen_manifest import main
    assert main(["--root", str(tmp_path)]) == 1


def test_atomic_write_leaves_no_tmp_file(tmp_path):
    topics = tmp_path / "topics"; topics.mkdir()
    (topics / "alpha.md").write_text("# Alpha\n> **TL;DR:** A hub.\n", encoding="utf-8")
    from gen_manifest import main
    assert main(["--root", str(tmp_path)]) == 0
    assert (tmp_path / "MANIFEST.md").exists()
    assert not (tmp_path / "MANIFEST.md.tmp").exists()
