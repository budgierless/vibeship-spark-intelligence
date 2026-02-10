# start_openclaw_spark.ps1 — Start all Spark ↔ OpenClaw services
$ErrorActionPreference = "SilentlyContinue"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $RepoRoot) { $RepoRoot = Split-Path -Parent $PSScriptRoot }
if (-not (Test-Path "$RepoRoot\sparkd.py")) { $RepoRoot = (Get-Location).Path }

Write-Host "=== Spark x OpenClaw — Starting ===" -ForegroundColor Cyan
Write-Host "Repo: $RepoRoot"

# 1. sparkd
Write-Host "`n[1/3] Starting sparkd..." -ForegroundColor Yellow
$sparkd = Start-Process -FilePath python -ArgumentList "$RepoRoot\sparkd.py" `
    -WorkingDirectory $RepoRoot -WindowStyle Hidden -PassThru
Write-Host "  PID: $($sparkd.Id)"

Start-Sleep -Seconds 2

# 2. bridge_worker
Write-Host "[2/3] Starting bridge_worker..." -ForegroundColor Yellow
$bridge = Start-Process -FilePath python -ArgumentList "$RepoRoot\bridge_worker.py" `
    -WorkingDirectory $RepoRoot -WindowStyle Hidden -PassThru
Write-Host "  PID: $($bridge.Id)"

# 3. openclaw_tailer
Write-Host "[3/3] Starting openclaw_tailer (with subagents)..." -ForegroundColor Yellow
$tailer = Start-Process -FilePath python -ArgumentList `
    "$RepoRoot\adapters\openclaw_tailer.py --include-subagents --verbose" `
    -WorkingDirectory $RepoRoot -WindowStyle Hidden -PassThru
Write-Host "  PID: $($tailer.Id)"

# Save PIDs for stop script
$pidFile = "$RepoRoot\scripts\.spark_pids.json"
@{
    sparkd  = $sparkd.Id
    bridge  = $bridge.Id
    tailer  = $tailer.Id
    started = (Get-Date -Format o)
} | ConvertTo-Json | Set-Content $pidFile

Write-Host "`n=== All services started ===" -ForegroundColor Green
Write-Host "PID file: $pidFile"
Write-Host "Stop with: scripts\stop_openclaw_spark.ps1"
