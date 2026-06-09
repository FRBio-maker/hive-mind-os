#!/usr/bin/env bash
# Thin launcher — forwards all arguments to bootstrap.py.
#
# macOS notes (read this if you're an agent driving the setup):
# ------------------------------------------------------------------
# macOS is native Unix, so the install is the SIMPLEST of the three OSes —
# but it diverges from the Linux and Windows paths in a few ways. Watch for:
#
# 1. SYMLINKS ARE FREE. Unlike Windows (which needs Developer Mode/admin or it
#    silently falls back to COPY), macOS creates symlinks with no special
#    privilege. bootstrap.py's copy-fallback should NEVER trigger here — if you
#    see a COPY in the output on a Mac, something is wrong (read-only dir,
#    missing parent), not a privilege issue. Investigate rather than accept it.
#
# 2. python3 MAY BE A STUB. Modern macOS ships NO `python` (Python 2 was removed
#    in macOS 12.3). `/usr/bin/python3` is a Command Line Tools *shim*: if the
#    CLT aren't installed, invoking it pops a GUI "install developer tools"
#    dialog and exits non-zero. This launcher probes python3 first and tells you
#    how to fix it if the probe fails:
#       xcode-select --install      # install the Command Line Tools, OR
#       brew install python         # Homebrew python3 (preferred if you use brew)
#
# 3. NO WSL. Ignore every WSL / mirrored-networking / `.cmd`-bridge instruction
#    in the docs — those are Windows-only. On a Mac you ARE the Unix box; the
#    Linux path applies directly, minus the VM. Codex/Gemini/Claude CLIs run
#    natively.
#
# 4. BSD COREUTILS != GNU. This bootstrap is pure Python, so it's immune. But
#    when you later wire the COMPANION tooling (hooks, skills, lint scripts),
#    any bash written for Linux may use GNU-isms that break on macOS's BSD
#    userland. The usual offenders to patch:
#       sed -i 's/x/y/' f      → BSD needs an arg:  sed -i '' 's/x/y/' f
#       readlink -f path       → absent on stock macOS; use `realpath` or
#                                `brew install coreutils` then `greadlink -f`
#       grep -P '...'          → BSD grep has no PCRE; use `grep -E` or `rg`
#       date -d '...'          → GNU-only; BSD `date` uses -v / -j -f
#    Prefer Python or portable POSIX in any script meant to run cross-OS.
#
# 5. CASE-INSENSITIVE FS (APFS default). The vault and identity files use
#    distinct names so this is fine here, but if you add files that differ only
#    by case (Foo.md vs foo.md), they collide on a default Mac volume.
#
# 6. EXECUTOR TIER (if you adopt it). On Apple Silicon, llama.cpp builds with
#    Metal acceleration and runs the GGUF models natively — no CUDA, no WSL GPU
#    bridge. This is a different (and simpler) setup than the Windows path in
#    docs/executor-tier.md; the OpenAI-compatible endpoint contract is identical.
# ------------------------------------------------------------------

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Probe for a REAL python3 (not the bare CLT stub, which fails this -c test).
if python3 -c "import sys; sys.exit(0)" 2>/dev/null; then
    exec python3 "$DIR/bootstrap.py" "$@"
else
    echo "error: a working python3 was not found." >&2
    echo "  macOS ships no 'python', and /usr/bin/python3 is a stub until the" >&2
    echo "  Command Line Tools are installed. Fix with ONE of:" >&2
    echo "    xcode-select --install      # Apple Command Line Tools" >&2
    echo "    brew install python         # Homebrew python3" >&2
    exit 1
fi
