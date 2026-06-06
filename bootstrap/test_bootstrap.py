"""
Tests for bootstrap.plan_actions().
Run from the bootstrap/ directory:
    python -m pytest test_bootstrap.py -q
"""
import os
import sys
import pathlib

import pytest

# Shim: ensure bootstrap.py (which lives beside this test) is importable.
sys.path.insert(0, str(pathlib.Path(__file__).parent))

import bootstrap  # noqa: E402 — after sys.path shim


def _symlinks_permitted(tmp_path) -> bool:
    """Probe whether this platform/process can create symlinks.

    On Windows without Developer Mode (or admin), os.symlink raises OSError.
    We use this to skip symlink-specific assertions instead of failing.
    """
    probe_target = tmp_path / "_probe_target"
    probe_target.write_text("x", encoding="utf-8")
    probe_link = tmp_path / "_probe_link"
    try:
        os.symlink(probe_target, probe_link)
    except OSError:
        return False
    finally:
        if probe_link.exists() or probe_link.is_symlink():
            try:
                probe_link.unlink()
            except OSError:
                pass
    return True


def test_plan_skips_existing(tmp_path):
    """When force=False and CLAUDE.md already exists, the action is marked skip."""
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "CLAUDE.md").write_text("existing", encoding="utf-8")
    actions = bootstrap.plan_actions(home=tmp_path, force=False)
    claude = [a for a in actions if a.dest.name == "CLAUDE.md"]
    assert claude, "No action found for CLAUDE.md"
    assert claude[0].skip is True


def test_plan_force_does_not_skip_existing(tmp_path):
    """When force=True, even an existing CLAUDE.md is NOT skipped."""
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "CLAUDE.md").write_text("existing", encoding="utf-8")
    actions = bootstrap.plan_actions(home=tmp_path, force=True)
    claude = [a for a in actions if a.dest.name == "CLAUDE.md"]
    assert claude, "No action found for CLAUDE.md"
    assert claude[0].skip is False


def test_apply_creates_dest_with_matching_content(tmp_path):
    """apply_actions on a fresh home creates each dest (symlink or copy) and
    the dest content matches the source content."""
    actions = bootstrap.plan_actions(home=tmp_path, force=False)
    bootstrap.apply_actions(actions)
    for action in actions:
        assert action.dest.exists(), f"dest not created: {action.dest}"
        assert action.dest.read_text(encoding="utf-8") == \
            action.src.read_text(encoding="utf-8"), \
            f"content mismatch at {action.dest}"


def test_apply_symlink_is_live(tmp_path):
    """When symlinks are permitted, the default install is a real symlink so
    edits to the repo file are seen live at the dest."""
    if not _symlinks_permitted(tmp_path):
        pytest.skip("symlinks not permitted on this platform")
    actions = bootstrap.plan_actions(home=tmp_path, force=False)
    bootstrap.apply_actions(actions)
    for action in actions:
        assert action.dest.is_symlink(), f"expected symlink at {action.dest}"
        assert action.method == "symlink"


def test_force_backs_up_existing_with_old_content(tmp_path):
    """With force=True over an existing dest, a <dest>.bak.<timestamp> file is
    created containing the OLD content before the new install."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    dest = claude_dir / "CLAUDE.md"
    old_content = "OLD-CONTENT-MARKER"
    dest.write_text(old_content, encoding="utf-8")

    actions = bootstrap.plan_actions(home=tmp_path, force=True)
    bootstrap.apply_actions(actions)

    backups = list(claude_dir.glob("CLAUDE.md.bak.*"))
    assert backups, "no backup file created"
    assert any(b.read_text(encoding="utf-8") == old_content for b in backups), \
        "no backup contained the old content"


def test_rollback_restores_most_recent_backup(tmp_path):
    """rollback(home) removes the installed dest and restores the most recent
    <dest>.bak.<timestamp> content to the dest."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    dest = claude_dir / "CLAUDE.md"
    old_content = "OLD-CONTENT-FOR-ROLLBACK"
    dest.write_text(old_content, encoding="utf-8")

    # Install over it with force → creates backup + installs new dest.
    actions = bootstrap.plan_actions(home=tmp_path, force=True)
    bootstrap.apply_actions(actions)

    # Roll back → dest should hold the old content again.
    bootstrap.rollback(home=tmp_path)
    assert dest.exists(), "dest missing after rollback"
    assert not dest.is_symlink(), "dest should be a restored real file, not a symlink"
    assert dest.read_text(encoding="utf-8") == old_content


def test_rollback_leaves_real_file_with_no_backup_intact(tmp_path):
    """KEY SAFETY TEST. A dest that is a real, hand-written file with NO
    <dest>.bak.* backup must be LEFT UNTOUCHED by rollback — never deleted.
    This is the case that previously destroyed a user's ~/.claude/CLAUDE.md."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    dest = claude_dir / "CLAUDE.md"
    user_content = "HAND-WRITTEN-USER-FILE-DO-NOT-DELETE"
    dest.write_text(user_content, encoding="utf-8")

    # No install happened, no backup exists. Roll back.
    bootstrap.rollback(home=tmp_path)

    assert dest.exists(), "rollback DELETED a real user file with no backup!"
    assert dest.read_text(encoding="utf-8") == user_content, \
        "rollback altered a real user file"


def test_rollback_removes_our_symlink_with_no_backup(tmp_path):
    """A dest that is a symlink WE installed (points into this repo) and has no
    backup should be removed by rollback (it's our install, not user data)."""
    if not _symlinks_permitted(tmp_path):
        pytest.skip("symlinks not permitted on this platform")

    # Fresh apply → creates symlinks into the repo, no backups.
    actions = bootstrap.plan_actions(home=tmp_path, force=False)
    bootstrap.apply_actions(actions)

    claude_dest = tmp_path / ".claude" / "CLAUDE.md"
    assert claude_dest.is_symlink(), "precondition: install should be a symlink"

    bootstrap.rollback(home=tmp_path)

    assert not (claude_dest.exists() or claude_dest.is_symlink()), \
        "rollback should remove a symlink we installed when no backup exists"


def test_rollback_leaves_foreign_symlink_with_no_backup_intact(tmp_path):
    """A symlink the USER made pointing somewhere OUTSIDE this repo, with no
    backup, must be left untouched — we only remove symlinks we installed."""
    if not _symlinks_permitted(tmp_path):
        pytest.skip("symlinks not permitted on this platform")

    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    dest = claude_dir / "CLAUDE.md"

    # A user-owned target OUTSIDE the repo, linked at dest.
    foreign_target = tmp_path / "user_notes.md"
    foreign_target.write_text("USER-OWNED-TARGET", encoding="utf-8")
    os.symlink(foreign_target, dest)

    bootstrap.rollback(home=tmp_path)

    assert dest.is_symlink(), "rollback removed a foreign (user) symlink!"
    assert dest.resolve() == foreign_target.resolve(), \
        "rollback altered the foreign symlink target"
