#!/usr/bin/env bash
# Thin launcher — forwards all arguments to bootstrap.py.
# Prefers 'python3'; falls back to 'python'.
# On Linux/macOS 'python3' is the canonical interpreter.
# On Windows Git Bash 'python' is the real interpreter ('python3' may be a
# Microsoft Store stub — test with -c to confirm it is real before using it).
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if python3 -c "import sys; sys.exit(0)" 2>/dev/null; then
    exec python3 "$DIR/bootstrap.py" "$@"
else
    exec python "$DIR/bootstrap.py" "$@"
fi
