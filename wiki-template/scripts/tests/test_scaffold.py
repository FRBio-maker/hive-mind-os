def test_new_cluster(tmp_path):
    from scaffold import new_cluster
    p = new_cluster(root=tmp_path, slug="my-thing", date="2026-06-06")
    summary = p / "_summary.md"
    assert summary.exists()
    text = summary.read_text(encoding="utf-8")
    assert "my-thing" in text and "2026-06-06" in text


def test_init_vault(tmp_path):
    from scaffold import init_vault
    vault = tmp_path / "fresh"
    init_vault(root=vault)
    assert (vault / "topics").is_dir()
    assert (vault / "nodes").is_dir()
    assert (vault / "_templates").is_dir()
    assert (vault / "SCHEMA.md").exists()
