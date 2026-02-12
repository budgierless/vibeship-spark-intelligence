# status_openclaw_spark.ps1 - Check health of Spark <-> OpenClaw services
$ErrorActionPreference = "SilentlyContinue"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $RepoRoot) { $RepoRoot = Split-Path -Parent $PSScriptRoot }
if (-not (Test-Path "$RepoRoot\sparkd.py")) { $RepoRoot = (Get-Location).Path }

$pidFile = "$RepoRoot\scripts\.spark_pids.json"
$sparkdPort = if ($env:SPARKD_PORT -match "^\d+$") { [int]$env:SPARKD_PORT } else { 8787 }

Write-Host "=== Spark x OpenClaw - Status ===" -ForegroundColor Cyan

if (Test-Path $pidFile) {
    $pids = Get-Content $pidFile | ConvertFrom-Json
    if ($pids.sparkd_port) { $sparkdPort = [int]$pids.sparkd_port }
    Write-Host "Started: $($pids.started)" -ForegroundColor DarkGray

    foreach ($svc in @("sparkd", "bridge", "tailer")) {
        $pid = $pids.$svc
        $proc = if ($pid) { Get-Process -Id $pid -ErrorAction SilentlyContinue } else { $null }
        if ($proc) {
            Write-Host "  [OK] $svc - PID $pid, CPU $([math]::Round($proc.CPU, 1))s" -ForegroundColor Green
        } else {
            Write-Host "  [DEAD] $svc - PID $pid not running" -ForegroundColor Red
        }
    }
} else {
    Write-Host "  No PID file found. Services may not be running." -ForegroundColor Yellow
}

# Check sparkd HTTP health
Write-Host "`nsparkd HTTP check:" -ForegroundColor Cyan
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$sparkdPort/health" -TimeoutSec 3 -UseBasicParsing
    Write-Host "  [OK] sparkd responding ($($resp.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] sparkd not responding on :$sparkdPort" -ForegroundColor Red
}

# Check report dir
$reportDir = Join-Path $env:USERPROFILE ".openclaw\workspace\spark_reports"
$reportCount = if (Test-Path $reportDir) { (Get-ChildItem "$reportDir\*.json" -ErrorAction SilentlyContinue).Count } else { 0 }
Write-Host "`nPending self-reports: $reportCount" -ForegroundColor $(if ($reportCount -gt 0) { "Yellow" } else { "DarkGray" })
