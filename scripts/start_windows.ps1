# Launch FinAlly as a desktop window (Windows).
# Requires Microsoft Edge WebView2 runtime (pywebview uses it on Windows).
# Builds the static UI if needed, syncs backend deps, then opens the window
# with the FastAPI sidecar running in-process on loopback.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $env:TEMP "finally.pid"

# 1) Build the Next.js static export if it hasn't been built yet.
if (-not (Test-Path (Join-Path $Root "frontend/out"))) {
    Write-Host "==> Building frontend static export"
    Push-Location (Join-Path $Root "frontend")
    npm install
    npm run build
    Pop-Location
}

# 2) Ensure backend + desktop dependencies are installed.
Write-Host "==> Syncing backend dependencies (desktop extra)"
Push-Location (Join-Path $Root "backend")
uv sync --extra desktop

# 3) Launch the desktop shell.
Write-Host "==> Launching FinAlly"
$proc = Start-Process -FilePath "uv" `
    -ArgumentList @("run", "--extra", "desktop", "python", (Join-Path $Root "desktop/main.py")) `
    -NoNewWindow -PassThru
Pop-Location
$proc.Id | Out-File -FilePath $PidFile -Encoding ascii
$proc.WaitForExit()
Remove-Item $PidFile -ErrorAction SilentlyContinue
