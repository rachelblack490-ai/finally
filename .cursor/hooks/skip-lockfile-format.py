#!/usr/bin/env python3
"""Do not format or rewrite generated lockfiles after an agent edit."""

from __future__ import annotations

import json
import sys
from pathlib import Path

LOCKFILE_NAMES = {
    "uv.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Cargo.lock",
}


def _paths(payload: dict) -> list[str]:
    keys = ("file_path", "filePath", "path", "file")
    found: list[str] = []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            found.append(value)
    files = payload.get("files")
    if isinstance(files, list):
        for item in files:
            if isinstance(item, str):
                found.append(item)
            elif isinstance(item, dict):
                found.extend(_paths(item))
    return found


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        json.dump({}, sys.stdout)
        return 0

    lock_hits = [
        path
        for path in _paths(payload)
        if Path(path).name in LOCKFILE_NAMES
    ]
    if lock_hits:
        json.dump(
            {
                "additional_context": (
                    "Lockfile edit detected "
                    f"({', '.join(lock_hits)}). Do not run formatters or "
                    "hand-edit generated lockfiles; use the package manager."
                )
            },
            sys.stdout,
        )
        return 0

    json.dump({}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
