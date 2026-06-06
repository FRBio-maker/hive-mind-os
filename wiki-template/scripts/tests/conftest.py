"""Make the scripts/ modules importable from tests/.

Tests live in scripts/tests/; the modules under test live one level up in
scripts/. Adding the parent dir to sys.path lets `from gen_manifest import ...`
resolve without an installed package or PYTHONPATH gymnastics.
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
