#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for FinAlly.
# Installs uv system-wide (if missing) and syncs the backend Python project.
#
# uv is installed to /usr/local/bin (a persistent system path that survives
# environment-build snapshots) rather than $HOME/.local/bin, so agents that
# boot from a prebuilt environment still have the toolchain available.
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "==> Installing uv into /usr/local/bin"
  tmp_dir="$(mktemp -d)"
  curl -LsSf https://astral.sh/uv/install.sh \
    | env UV_INSTALL_DIR="$tmp_dir" INSTALLER_NO_MODIFY_PATH=1 sh
  sudo install -m 0755 "$tmp_dir/uv" /usr/local/bin/uv
  sudo install -m 0755 "$tmp_dir/uvx" /usr/local/bin/uvx
  rm -rf "$tmp_dir"
else
  echo "==> uv already installed: $(command -v uv) ($(uv --version))"
fi

echo "==> Syncing backend dependencies (uv sync --extra dev)"
cd "$(dirname "$0")/../backend"
uv sync --extra dev

echo "==> FinAlly backend environment ready"
uv run python -c "import fastapi, numpy, massive, rich; print('core deps import OK')"
