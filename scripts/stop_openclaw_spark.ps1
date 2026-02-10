# stop_openclaw_spark.ps1 — Stop all Spark ↔ OpenClaw services
$ErrorActionPreference = "SilentlyContinue"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $RepoRoot) { $RepoRoot = Split-Path -Parent $PSScriptRoot }
if (-not (Test-Path "$RepoRoot\sparkd.py")) { $RepoRoot = (Get-Location).Path }

$pidFile = "$RepoRoot\scripts\.spark_pids.json"

Write-Host "=== Spark x OpenClaw — Stopping ===" -ForegroundColor Cyan

if (Test-Path $pidFile) {
    $pids = Get-Content $pidFile | ConvertFrom-Json
    foreach ($svc in @("tailer", "bridge", "sparkd")) {
        $pid = $pids.$svc
        if ($pid) {
            $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($proc) {
                Stop-Process -Id $pid -Force
                Write-Host "  Stopped $svc (PID $pid)" -ForegroundColor Yellow
            } else {
                Write-Host "  $svc (PID $pid) already stopped" -ForegroundColor DarkGray
            }
        }
    }
    Remove-Item $pidFile -Force
} else {
    Write-Host "No PID file found. Trying to find processes by name..." -ForegroundColor Yellow
    # Fallback: kill python processes matching our scripts
    Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -match "sparkd|bridge_worker|openclaw_tailer"
    } | ForEach-Object {
        Stop-Process -Id $_.Id -Force
        Write-Host "  Killed PID $($_.Id)" -ForegroundColor Yellow
    }
}

Write-Host "`n=== Stopped ===" -ForegroundColor Green
