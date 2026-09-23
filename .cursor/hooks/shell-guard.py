#!/usr/bin/env python3
"""Ask before docker / destructive rm; allow common FinAlly dev commands."""

from __future__ import annotations

import json
import re
import sys

ASK_PATTERNS = (
    re.compile(r"\bdocker\b", re.I),
    re.compile(r"\bdocker-compose\b", re.I),
    re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f\b"),
    re.compile(r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r\b"),
)

ALLOW_PREFIXES = (
    "uv ",
    "uv\t",
    "pytest",
    "npm ",
    "npx ",
    "node ",
    "pnpm ",
    "yarn ",
    "ruff ",
    "python ",
    "python3 ",
    "git status",
    "git diff",
    "git log",
    "git add ",
)


def _command(payload: dict) -> str:
    return str(payload.get("command") or payload.get("cmd") or "").strip()


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        json.dump({"permission": "allow"}, sys.stdout)
        return 0

    command = _command(payload)
    if not command:
        json.dump({"permission": "allow"}, sys.stdout)
        return 0

    for prefix in ALLOW_PREFIXES:
        if command.startswith(prefix) or command == prefix.strip():
            json.dump({"permission": "allow"}, sys.stdout)
            return 0

    for pattern in ASK_PATTERNS:
        if pattern.search(command):
            json.dump(
                {
                    "permission": "ask",
                    "user_message": "This command looks destructive or Docker-based. FinAlly launches via pywebview, not Docker.",
                    "agent_message": "A project hook asked for approval because the shell command matches docker or rm -rf.",
                },
                sys.stdout,
            )
            return 0

    json.dump({"permission": "allow"}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
