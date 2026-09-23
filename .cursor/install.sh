#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for the FinAlly backend (uv project).
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

# Ensure the uv package manager is available (no-op if already installed).
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

export PATH="$HOME/.local/bin:$PATH"

# Install backend dependencies (incl. dev tools) from the committed lockfile.
cd "$(dirname "$0")/../backend"
uv sync --extra dev
