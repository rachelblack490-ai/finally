#!/usr/bin/env bash
# Start the FinAlly sidecar for E2E: simulator + mock LLM + a temp DB, serving
# the built static export on one loopback origin.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Build the static export if it isn't present.
if [ ! -d "$ROOT/frontend/out" ]; then
  (cd "$ROOT/frontend" && npm install && npm run build)
fi

export LLM_MOCK=true
export MASSIVE_API_KEY=""
export FINALLY_HOST=127.0.0.1
export FINALLY_PORT="${FINALLY_PORT:-8055}"
export FINALLY_STATIC_DIR="$ROOT/frontend/out"
export FINALLY_DB_PATH="${FINALLY_DB_PATH:-/tmp/finally_e2e.db}"
rm -f "$FINALLY_DB_PATH" "$FINALLY_DB_PATH"-* 2>/dev/null || true

cd "$ROOT/backend"
exec uv run python -m app
