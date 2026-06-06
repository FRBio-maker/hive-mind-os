"""
bootstrap.py — cross-platform installer for hive-mind-os identity files.

Behavior
--------
- Dry-run by DEFAULT: prints the plan, writes nothing.
- Requires --apply to actually install files.
- Installs each identity file as a SYMLINK by default (write-through: edits to
  the repo file are seen live at the runtime dest). If the OS forbids symlinks
  (e.g. Windows without Developer Mode / admin), falls back to a real copy and
  reports the action as a COPY.
- Skips existing destination files unless --force is passed.
- With --force, an existing dest is moved to <dest>.bak.<YYYYMMDD-HHMMSS>
  BEFORE the new symlink/copy is written — never destroys data.
- --rollback removes each installed symlink/file and restores the most recent
  <dest>.bak.<timestamp> if one exists.

Planned installs
-----------------
  identity/CLAUDE.md  → ~/.claude/CLAUDE.md
  identity/AGENTS.md  → ~/.codex/AGENTS.md
  identity/GEMINI.md  → ~/.gemini/GEMINI.md
  identity/GROK.md    → ~/.grok/AGENTS.md   (Grok reads AGENTS.md)

Usage
-----
  python bootstrap.py                  # dry-run: print plan only
  python bootstrap.py --apply          # install (symlink; skip existing)
  python bootstrap.py --apply --force  # install, backing up existing dests
  python bootstrap.py --rollback       # remove installs, restore latest backups
"""

import argparse
import datetime
import os
import pathlib
import shutil
import sys
from typing import NamedTuple, List, Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class Action(NamedTuple):
    """A single planned install operation.

    method : "symlink" | "copy" | "skip"
        The intended method. plan_actions() always proposes "symlink" for
        installs and "skip" for existing dests without --force. apply_actions()
        may downgrade "symlink" → "copy" at runtime if the OS forbids symlinks.
    backup : Optional[pathlib.Path]
        Where the pre-existing dest was moved before clobbering (set by
        apply_actions when a backup happens). None otherwise.
    """
    src: pathlib.Path           # source file (inside this repo's identity/ dir)
    dest: pathlib.Path          # destination (inside the agent's runtime dir)
    skip: bool                  # True → existing dest and --force not given
    method: str = "symlink"     # "symlink" | "copy" | "skip"
    backup: Optional[pathlib.Path] = None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _repo_root() -> pathlib.Path:
    """Return the hive-mind-os repo root (parent of bootstrap/)."""
    return pathlib.Path(__file__).resolve().parent.parent


def _mappings(home: pathlib.Path):
    """Return the (src_name, dest_dir, dest_name) install mappings."""
    return [
        ("CLAUDE.md",  home / ".claude",  "CLAUDE.md"),
        ("AGENTS.md",  home / ".codex",   "AGENTS.md"),
        ("GEMINI.md",  home / ".gemini",  "GEMINI.md"),
        ("GROK.md",    home / ".grok",    "AGENTS.md"),
    ]


def _timestamp() -> str:
    """Return a filesystem-safe timestamp: YYYYMMDD-HHMMSS."""
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def plan_actions(home: pathlib.Path = None, force: bool = False) -> List[Action]:
    """
    Build the list of install actions without writing anything.

    Parameters
    ----------
    home : pathlib.Path, optional
        Home directory to use as the base for ~/.claude etc.
        Defaults to pathlib.Path.home().
    force : bool
        When False (default), actions whose dest already exists are marked
        skip=True (method="skip"). When True, existing files are overwritten
        (skip=False) after a backup is taken at apply time.

    Returns
    -------
    List[Action]
    """
    if home is None:
        home = pathlib.Path.home()

    repo = _repo_root()
    identity = repo / "identity"

    actions = []
    for src_name, dest_dir, dest_name in _mappings(home):
        src = identity / src_name
        dest = dest_dir / dest_name
        # A dest "exists" if it's a real file/dir OR a (possibly broken) symlink.
        exists = dest.exists() or dest.is_symlink()
        skip = (not force) and exists
        actions.append(Action(
            src=src,
            dest=dest,
            skip=skip,
            method="skip" if skip else "symlink",
        ))

    return actions


def _backup_existing(dest: pathlib.Path) -> Optional[pathlib.Path]:
    """Move an existing dest (real file or symlink) to <dest>.bak.<timestamp>.

    Returns the backup path, or None if there was nothing to back up. Uses
    shutil.move so a symlink is moved as-is (the link, not its target) when
    possible; for symlinks we recreate rather than copy the target.
    """
    if not (dest.exists() or dest.is_symlink()):
        return None

    backup = dest.with_name(f"{dest.name}.bak.{_timestamp()}")
    # If a same-second backup already exists, disambiguate to avoid clobbering.
    counter = 1
    while backup.exists() or backup.is_symlink():
        backup = dest.with_name(f"{dest.name}.bak.{_timestamp()}.{counter}")
        counter += 1

    if dest.is_symlink():
        # Preserve the link itself: read its target, recreate at backup, drop dest.
        target = os.readlink(dest)
        os.symlink(target, backup)
        dest.unlink()
    else:
        shutil.move(str(dest), str(backup))
    return backup


def _install_one(action: Action) -> Action:
    """Install a single action's dest. Returns an updated Action recording the
    real method used ("symlink" or "copy") and any backup taken.

    Falls back to copy if symlink creation raises OSError (Windows without
    Developer Mode / privilege) — never crashes on a symlink-permission error.
    """
    action.dest.parent.mkdir(parents=True, exist_ok=True)

    backup = _backup_existing(action.dest)

    # Use an absolute source path so the symlink resolves no matter the CWD.
    src_abs = action.src.resolve()

    method = "symlink"
    try:
        os.symlink(src_abs, action.dest)
    except OSError:
        # Symlinks not permitted (typical on Windows w/o Developer Mode).
        # Fall back to a real copy and record that fact for the caller to warn.
        try:
            shutil.copy2(src_abs, action.dest)
            method = "copy"
        except OSError:
            # Transactional safety: BOTH symlink and copy failed. If we took a
            # backup, the user would otherwise be left with NOTHING at dest.
            # Restore the backup so we never destroy the pre-existing file.
            if backup is not None:
                if backup.is_symlink():
                    target = os.readlink(backup)
                    os.symlink(target, action.dest)
                    backup.unlink()
                else:
                    shutil.move(str(backup), str(action.dest))
                print(f"  RESTORE {action.dest}  (install failed — backup restored)")
            raise

    return action._replace(method=method, backup=backup)


def apply_actions(actions: List[Action]) -> List[Action]:
    """
    Execute install operations for actions where skip=False.

    Creates parent dirs as needed. For each non-skipped action, backs up any
    existing dest to <dest>.bak.<timestamp> first, then symlinks (or copies on
    fallback). Returns the list of actions updated with the real method/backup.
    """
    results: List[Action] = []
    for action in actions:
        if action.skip:
            print(f"  SKIP  {action.dest}  (already exists; use --force to overwrite)")
            results.append(action)
            continue

        done = _install_one(action)
        if done.backup is not None:
            print(f"  BACKUP {done.dest}  →  {done.backup.name}")
        verb = "LINK" if done.method == "symlink" else "COPY"
        print(f"  {verb}  {done.src.name}  →  {done.dest}")
        if done.method == "copy":
            print("        (symlinks not permitted here — wrote a COPY; "
                  "edits to the repo file will NOT propagate. "
                  "Enable Developer Mode for live symlinks.)")
        results.append(done)
    return results


def _is_symlink_into_repo(dest: pathlib.Path, repo: pathlib.Path) -> bool:
    """True iff `dest` is a symlink whose target resolves INSIDE `repo`.

    This is how we tell "something we installed" (a link into this repo's
    identity/ dir) from "a real file the user wrote" or "a symlink the user
    made pointing somewhere else". We resolve the link target and check
    containment. Resolution failures (broken/circular links) → False (be safe:
    don't claim ownership of something we can't prove we created).
    """
    if not dest.is_symlink():
        return False
    try:
        # Resolve the LINK (dest) rather than parsing os.readlink() directly:
        # pathlib.resolve() follows the link AND normalizes Windows
        # extended-length prefixes (\\?\C:\...), which a raw readlink leaves in
        # place and would break the containment check below.
        target = dest.resolve()
        repo_resolved = repo.resolve()
        # Python 3.9+: is_relative_to. Fall back to a manual prefix check.
        try:
            return target.is_relative_to(repo_resolved)
        except AttributeError:  # pragma: no cover — Python < 3.9
            return str(target).startswith(str(repo_resolved) + os.sep)
    except OSError:
        return False


def rollback(home: pathlib.Path = None) -> List[Action]:
    """
    Undo an install SAFELY: for each dest, restore the most recent
    <dest>.bak.<timestamp> if one exists; otherwise only remove the dest when
    we can prove WE installed it (a symlink pointing into this repo).

    Safety contract (per dest):
      - Backup exists  → remove current dest, move newest backup into place.
                         Reported as RESTORE.
      - No backup, dest is a symlink INTO this repo (something we installed)
                       → remove it. Reported as REMOVE.
      - No backup, dest is a real file OR a symlink pointing elsewhere
                       → LEAVE UNTOUCHED. Reported as SKIP (not installed by us).

    This guarantees --rollback can NEVER delete a hand-written user file (or a
    user's own symlink) that we never installed and have no backup for.

    Returns a list of Actions describing what happened (method="copy" when a
    backup was restored, "symlink" when an our-symlink was removed, "skip" when
    nothing was touched).
    """
    if home is None:
        home = pathlib.Path.home()

    repo = _repo_root()
    identity = repo / "identity"

    results: List[Action] = []
    for src_name, dest_dir, dest_name in _mappings(home):
        src = identity / src_name
        dest = dest_dir / dest_name

        # Find the newest backup for this dest.
        backups = sorted(
            dest_dir.glob(f"{dest_name}.bak.*"),
            key=lambda p: p.name,
        ) if dest_dir.exists() else []
        latest = backups[-1] if backups else None

        if latest is not None:
            # We have a backup → safe to remove current dest and restore it.
            if dest.exists() or dest.is_symlink():
                dest.unlink()
                print(f"  REMOVE  {dest}")
            shutil.move(str(latest), str(dest))
            print(f"  RESTORE {latest.name}  →  {dest}")
            results.append(Action(src=src, dest=dest, skip=False,
                                  method="copy", backup=latest))
            continue

        # No backup. Only remove dest if it's a symlink WE created (into repo).
        if _is_symlink_into_repo(dest, repo):
            dest.unlink()
            print(f"  REMOVE  {dest}  (our symlink; no backup)")
            results.append(Action(src=src, dest=dest, skip=False,
                                  method="symlink", backup=None))
        else:
            # Real file, or someone else's symlink, or nothing there →
            # leave it. NEVER destroy a file we didn't install with no backup.
            print(f"  SKIP    {dest}  (not installed by us — left untouched)")
            results.append(Action(src=src, dest=dest, skip=True, method="skip"))

    return results


def print_plan(actions: List[Action]) -> None:
    """Print a human-readable dry-run summary."""
    print("Dry-run plan (pass --apply to install, --rollback to undo):")
    print()
    for action in actions:
        if action.skip:
            status = "SKIP (exists)"
        else:
            status = "SYMLINK"
        print(f"  [{status:14s}]  {action.src.name}  →  {action.dest}")
    print()
    installs = sum(1 for a in actions if not a.skip)
    skips = sum(1 for a in actions if a.skip)
    print(f"  {installs} file(s) to install (symlink), {skips} file(s) to skip.")
    print("  (Existing dests are backed up to <dest>.bak.<timestamp> when --force is used.)")
    print("  (On systems without symlink privilege, installs fall back to a real copy.)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="bootstrap",
        description=(
            "Install hive-mind-os identity files into agent runtime directories "
            "as symlinks (write-through). Dry-run by default — pass --apply to "
            "install or --rollback to undo."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Install files to disk (symlink, copy fallback). Without this flag, only print the plan.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Overwrite existing dests, backing each up to <dest>.bak.<timestamp> first.",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        default=False,
        help="Remove installed symlinks/files and restore the most recent <dest>.bak.<timestamp>.",
    )
    args = parser.parse_args(argv)

    if args.rollback:
        print("Rolling back bootstrap installs...")
        rollback()
        print("Done.")
        return 0

    actions = plan_actions(force=args.force)

    if args.apply:
        print("Applying bootstrap plan...")
        results = apply_actions(actions)
        if any(a.method == "copy" for a in results):
            print()
            print("WARNING: some files were COPIED, not symlinked (no symlink "
                  "privilege). Edits to repo identity files will not propagate "
                  "live. Enable Developer Mode (Windows) and re-run for symlinks.")
        print("Done.")
    else:
        print_plan(actions)

    return 0


if __name__ == "__main__":
    sys.exit(main())
