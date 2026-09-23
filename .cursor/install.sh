#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for FinAlly.
# Installs uv (if missing) and syncs the backend Python project.
set -euo pipefail

# Ensure the standard user-local bin dir (where uv installs) is on PATH.
export PATH="$HOME/.local/bin:$PATH"

if ! command -v uv >/dev/null 2>&1; then
  echo "==> Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
else
  echo "==> uv already installed: $(uv --version)"
fi

echo "==> Syncing backend dependencies (uv sync --extra dev)"
cd "$(dirname "$0")/../backend"
uv sync --extra dev

echo "==> FinAlly backend environment ready"
uv run python -c "import fastapi, numpy, massive, rich; print('core deps import OK')"
