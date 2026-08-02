"""Tests for session_start_hook.py.

The hook must emit a Claude Code SessionStart JSON envelope on stdout
(raw markdown would NOT be injected into the agent's context), and it
must never fail session startup: any regeneration error degrades to a
stale/partial envelope with an explicit warning, always exit 0.
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "session_start_hook.py"


def _make_vault(tmp_path: Path) -> Path:
    """Create a minimal vault with one topic hub and an empty nodes/ dir."""
    topics = tmp_path / "topics"
    topics.mkdir(parents=True)
    (tmp_path / "nodes").mkdir()
    hub = topics / "agent-protocols.md"
    hub.write_text(
        "# Agent Protocols\n\n"
        "> **TL;DR (≤80 words):** How agents coordinate, delegate, and "
        "share knowledge across runtimes.\n\n"
        "Detail goes here.\n",
        encoding="utf-8",
    )
    return tmp_path


def _run(*extra_args) -> subprocess.CompletedProcess:
    """Run the hook and return raw bytes result (avoids codec issues on Windows)."""
    return subprocess.run(
        [sys.executable, str(SCRIPT)] + list(extra_args),
        capture_output=True,
    )


def _envelope(result: subprocess.CompletedProcess) -> dict:
    """Parse stdout as the SessionStart JSON envelope."""
    stdout = result.stdout.decode("utf-8", errors="replace")
    return json.loads(stdout)


def test_envelope_shape_and_manifest_injected(tmp_path):
    """Healthy vault: exit 0, valid envelope, hub appears in additionalContext."""
    vault = _make_vault(tmp_path)
    result = _run("--root", str(vault))

    assert result.returncode == 0, (
        f"Non-zero exit.\nstderr: {result.stderr.decode('utf-8', errors='replace')}"
    )
    env = _envelope(result)
    hso = env["hookSpecificOutput"]
    assert hso["hookEventName"] == "SessionStart"
    assert env["continue"] is True
    assert env["suppressOutput"] is True
    # The hub slug must appear in the injected context.
    assert "agent-protocols" in hso["additionalContext"]


def test_manifest_file_written(tmp_path):
    """The hook regenerates MANIFEST.md on disk at the vault root."""
    vault = _make_vault(tmp_path)
    _run("--root", str(vault))

    manifest_file = vault / "MANIFEST.md"
    assert manifest_file.exists(), "MANIFEST.md was not written"
    assert "agent-protocols" in manifest_file.read_text(encoding="utf-8")


def test_work_queue_digest_present(tmp_path):
    """The envelope carries the <=10-line work-queue digest section."""
    vault = _make_vault(tmp_path)
    result = _run("--root", str(vault))

    ctx = _envelope(result)["hookSpecificOutput"]["additionalContext"]
    assert "work-queue digest" in ctx


def test_missing_topics_still_emits_envelope(tmp_path):
    """Failure isolation: broken vault (no topics/) must NOT block startup.

    Exit 0, valid JSON envelope, manifest reported unavailable.
    """
    result = _run("--root", str(tmp_path))

    assert result.returncode == 0
    env = _envelope(result)
    ctx = env["hookSpecificOutput"]["additionalContext"]
    assert env["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "unavailable" in ctx or "crashed" in ctx


def test_stale_manifest_fallback_with_warning(tmp_path):
    """Regeneration fails but a previous MANIFEST.md exists on disk:
    inject the stale manifest behind an explicit STALE warning banner."""
    (tmp_path / "MANIFEST.md").write_text(
        "# Wiki Manifest\n\n- [[topics/old-hub]] — from a previous session\n",
        encoding="utf-8",
    )
    # No topics/ dir -> gen_manifest exits 1 -> stale path taken.
    result = _run("--root", str(tmp_path))

    assert result.returncode == 0
    ctx = _envelope(result)["hookSpecificOutput"]["additionalContext"]
    assert "STALE" in ctx
    assert "old-hub" in ctx
