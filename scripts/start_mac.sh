#!/usr/bin/env bash
# Launch FinAlly as a desktop window (macOS). Builds the static UI if needed,
# syncs backend deps, then opens the pywebview window with the sidecar running
# in-process on loopback. Closing the window stops the sidecar.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIDFILE="${TMPDIR:-/tmp}/finally.pid"

# 1) Build the Next.js static export if it hasn't been built yet.
if [ ! -d "$ROOT/frontend/out" ]; then
  echo "==> Building frontend static export"
  (cd "$ROOT/frontend" && npm install && npm run build)
fi

# 2) Ensure backend + desktop dependencies are installed.
echo "==> Syncing backend dependencies (desktop extra)"
(cd "$ROOT/backend" && uv sync --extra desktop)

# 3) Launch the desktop shell (FastAPI sidecar runs in-process on 127.0.0.1).
echo "==> Launching FinAlly"
cd "$ROOT/backend"
uv run --extra desktop python "$ROOT/desktop/main.py" &
APP_PID=$!
echo "$APP_PID" > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT
wait "$APP_PID"
