def test_manifest_lists_hubs(tmp_path):
    topics = tmp_path / "topics"; topics.mkdir()
    (topics / "alpha.md").write_text("---\ntype: topic\n---\n# Alpha\n> **TL;DR:** First hub.\n", encoding="utf-8")
    (topics / "beta.md").write_text("---\ntype: topic\n---\n# Beta\n> **TL;DR:** Second hub.\n", encoding="utf-8")
    from gen_manifest import build_manifest
    out = build_manifest(root=tmp_path)
    assert "alpha" in out and "First hub." in out
    assert "beta" in out and "Second hub." in out
