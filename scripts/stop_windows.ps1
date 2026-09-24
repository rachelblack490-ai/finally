# Stop the FinAlly desktop app / sidecar if it is still running (Windows).
$ErrorActionPreference = "SilentlyContinue"

$PidFile = Join-Path $env:TEMP "finally.pid"

if (Test-Path $PidFile) {
    $procId = Get-Content $PidFile
    if ($procId) {
        Stop-Process -Id ([int]$procId) -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped FinAlly (pid $procId)"
    }
    Remove-Item $PidFile -ErrorAction SilentlyContinue
} else {
    Write-Host "FinAlly not running (no pidfile at $PidFile)"
}
