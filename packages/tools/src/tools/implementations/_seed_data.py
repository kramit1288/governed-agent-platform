"""Seed data loaders shared by deterministic local V1 tools."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
SEED_DIR = ROOT / "data" / "seed"


@lru_cache(maxsize=None)
def load_seed_records(name: str) -> list[dict[str, Any]]:
    """Load a seeded JSON collection once per process."""

    path = SEED_DIR / f"{name}.json"
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_record(collection: str, key_name: str, key_value: str) -> dict[str, Any]:
    """Find a record in a named seed collection or raise a clear error."""

    for record in load_seed_records(collection):
        if record.get(key_name) == key_value:
            return record
    raise LookupError(f"{collection.rstrip('s').replace('_', ' ')} '{key_value}' was not found.")
