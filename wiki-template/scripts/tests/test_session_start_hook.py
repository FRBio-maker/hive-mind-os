"""Tests for session_start_hook.py.

Verifies that running the hook against a minimal vault prints the manifest
to stdout (so the runtime can inject it) and that the hub name appears in
the output.
"""

import subprocess
import sys
from pathlib import Path


def _make_vault(tmp_path: Path) -> Path:
    """Create a minimal vault with one topic hub."""
    topics = tmp_path / "topics"
    topics.mkdir(parents=True)
    hub = topics / "agent-protocols.md"
    hub.write_text(
        "# Agent Protocols\n\n"
        "> **TL;DR (≤80 words):** How agents coordinate, delegate, and "
        "share knowledge across runtimes.\n\n"
        "Detail goes here.\n",
        encoding="utf-8",
    )
    return tmp_path


def _run(script: Path, *extra_args) -> subprocess.CompletedProcess:
    """Run the script and return raw bytes result (avoids codec issues on Windows)."""
    return subprocess.run(
        [sys.executable, str(script)] + list(extra_args),
        capture_output=True,
    )


def test_hub_appears_in_stdout(tmp_path):
    """Running the hook against a vault with one hub prints the hub to stdout."""
    vault = _make_vault(tmp_path)
    script = Path(__file__).parent.parent / "session_start_hook.py"
    result = _run(script, "--root", str(vault))

    assert result.returncode == 0, (
        f"Non-zero exit.\nstderr: {result.stderr.decode('utf-8', errors='replace')}"
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    # The hub slug should appear in the manifest output.
    assert "agent-protocols" in stdout, (
        f"Expected 'agent-protocols' in stdout.\nGot:\n{stdout}"
    )


def test_missing_topics_exits_nonzero(tmp_path):
    """A vault with no topics/ directory should exit 1."""
    script = Path(__file__).parent.parent / "session_start_hook.py"
    result = _run(script, "--root", str(tmp_path))

    assert result.returncode == 1
    stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    assert "ERROR" in stderr


def test_manifest_file_written(tmp_path):
    """The hook must also write MANIFEST.md to the vault root."""
    vault = _make_vault(tmp_path)
    script = Path(__file__).parent.parent / "session_start_hook.py"
    _run(script, "--root", str(vault))

    manifest_file = vault / "MANIFEST.md"
    assert manifest_file.exists(), "MANIFEST.md was not written"
    assert "agent-protocols" in manifest_file.read_text(encoding="utf-8")
