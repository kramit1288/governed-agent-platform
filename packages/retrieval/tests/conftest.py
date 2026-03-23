"""Pytest configuration for retrieval tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for package in ("retrieval", "db"):
    src = ROOT / "packages" / package / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
