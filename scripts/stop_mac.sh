#!/usr/bin/env bash
# Stop the FinAlly desktop app / sidecar if it is still running (macOS).
set -euo pipefail

PIDFILE="${TMPDIR:-/tmp}/finally.pid"

if [ -f "$PIDFILE" ]; then
  PID="$(cat "$PIDFILE")"
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    echo "Stopped FinAlly (pid $PID)"
  else
    echo "FinAlly process $PID not running"
  fi
  rm -f "$PIDFILE"
else
  echo "FinAlly not running (no pidfile at $PIDFILE)"
fi
