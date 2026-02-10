<#
.SYNOPSIS
    Spark Intelligence - one command to rule them all.
.DESCRIPTION
    spark start    - Start all services
    spark stop     - Stop all services  
    spark status   - Show live status
    spark restart  - Stop then start
    spark health   - Quick health check
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "status", "restart", "health")]
    [string]$Action = "status"
)

$REPO = "C:\Users\USER\Desktop\vibeship-spark-intelligence"
$PULSE_DIR = "C:\Users\USER\Desktop\vibeship-spark-pulse"
$PID_FILE = "$REPO\scripts\.spark_pids.json"

function Save-Pids($pids) {
    $pids | ConvertTo-Json | Set-Content $PID_FILE -Encoding UTF8
}

function Load-Pids {
    if (Test-Path $PID_FILE) {
        try { return Get-Content $PID_FILE -Raw | ConvertFrom-Json }
        catch { return $null }
    }
    return $null
}

function Start-Spark {
    Write-Host ""
    Write-Host "  [*] Starting Spark Intelligence..." -ForegroundColor Cyan
    Write-Host ""

    $existing = Load-Pids
    if ($existing) {
        $alive = 0
        @($existing.sparkd, $existing.bridge, $existing.tailer, $existing.pulse) | ForEach-Object {
            if ($_ -and (Get-Process -Id $_ -ErrorAction SilentlyContinue)) { $alive++ }
        }
        if ($alive -ge 3) {
            Write-Host "  [!] Spark is already running ($alive services). Use 'spark restart'." -ForegroundColor Yellow
            return
        }
    }

    Stop-Spark -Quiet

    $env:SPARK_EMBEDDINGS = "0"

    $sparkd = Start-Process python -ArgumentList "$REPO\sparkd.py" -WorkingDirectory $REPO -WindowStyle Hidden -PassThru
    Start-Sleep 1
    $bridge = Start-Process python -ArgumentList "$REPO\bridge_worker.py" -WorkingDirectory $REPO -WindowStyle Hidden -PassThru
    $tailer = Start-Process python -ArgumentList "$REPO\adapters\openclaw_tailer.py","--include-subagents" -WorkingDirectory $REPO -WindowStyle Hidden -PassThru
    $pulse = Start-Process python -ArgumentList "-m","uvicorn","app:app","--host","127.0.0.1","--port","8765" -WorkingDirectory $PULSE_DIR -WindowStyle Hidden -PassThru

    Save-Pids @{
        sparkd = $sparkd.Id
        bridge = $bridge.Id
        tailer = $tailer.Id
        pulse = $pulse.Id
        started = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    }

    Start-Sleep 3

    $ok = 0
    foreach ($svc in @(
        @{Name="sparkd"; PID=$sparkd.Id},
        @{Name="bridge_worker"; PID=$bridge.Id},
        @{Name="tailer"; PID=$tailer.Id},
        @{Name="pulse"; PID=$pulse.Id}
    )) {
        if (Get-Process -Id $svc.PID -ErrorAction SilentlyContinue) {
            Write-Host "  [OK] $($svc.Name.PadRight(15)) PID $($svc.PID)" -ForegroundColor Green
            $ok++
        } else {
            Write-Host "  [FAIL] $($svc.Name)" -ForegroundColor Red
        }
    }

    Write-Host ""
    if ($ok -eq 4) {
        Write-Host "  Spark Intelligence is LIVE! ($ok services)" -ForegroundColor Green
        Write-Host "  Dashboard: http://localhost:8765" -ForegroundColor Cyan
    } else {
        Write-Host "  Spark partially started ($ok of 4 services)" -ForegroundColor Yellow
    }
    Write-Host ""
}

function Stop-Spark {
    param([switch]$Quiet)
    
    if (-not $Quiet) {
        Write-Host ""
        Write-Host "  Stopping Spark Intelligence..." -ForegroundColor Yellow
    }

    $pids = Load-Pids
    $killed = 0

    if ($pids) {
        @($pids.sparkd, $pids.bridge, $pids.tailer, $pids.pulse) | ForEach-Object {
            if ($_ -and (Get-Process -Id $_ -ErrorAction SilentlyContinue)) {
                Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
                $killed++
            }
        }
    }

    # Kill orphans
    Get-WmiObject Win32_Process -Filter "Name='python.exe'" | Where-Object {
        $_.CommandLine -like "*bridge_worker*" -or
        $_.CommandLine -like "*sparkd.py*" -or
        $_.CommandLine -like "*openclaw_tailer*" -or
        ($_.CommandLine -like "*uvicorn*" -and $_.CommandLine -like "*8765*")
    } | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        $killed++
    }

    if ($PID_FILE -and (Test-Path $PID_FILE)) { Remove-Item $PID_FILE -Force }

    if (-not $Quiet) {
        Write-Host "  Stopped $killed processes" -ForegroundColor Yellow
        Write-Host ""
    }
}

function Show-Status {
    Write-Host ""
    Write-Host "  ==========================================" -ForegroundColor Cyan
    Write-Host "  SPARK INTELLIGENCE STATUS" -ForegroundColor Cyan
    Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray
    Write-Host "  ==========================================" -ForegroundColor Cyan

    Write-Host ""
    Write-Host "  SERVICES" -ForegroundColor White
    $pids = Load-Pids
    $alive = 0
    if ($pids) {
        foreach ($svc in @(
            @{Name="sparkd"; PID=$pids.sparkd},
            @{Name="bridge_worker"; PID=$pids.bridge},
            @{Name="tailer"; PID=$pids.tailer},
            @{Name="pulse"; PID=$pids.pulse}
        )) {
            $proc = Get-Process -Id $svc.PID -ErrorAction SilentlyContinue
            if ($proc) {
                $mem = [math]::Round($proc.WorkingSet64/1MB)
                Write-Host ("  [OK] {0} PID {1}  {2}MB" -f $svc.Name.PadRight(15), $svc.PID, $mem) -ForegroundColor Green
                $alive++
            } else {
                Write-Host ("  [--] {0} DOWN" -f $svc.Name.PadRight(15)) -ForegroundColor Red
            }
        }
        $total = [math]::Round((Get-Process python -ErrorAction SilentlyContinue | Measure-Object -Property WorkingSet64 -Sum).Sum/1MB)
        Write-Host "  Total RAM: ${total}MB" -ForegroundColor DarkGray
    } else {
        Write-Host "  Not running. Use 'spark start'" -ForegroundColor Yellow
    }

    $hbFile = "$env:USERPROFILE\.spark\bridge_worker_heartbeat.json"
    if (Test-Path $hbFile) {
        $hb = Get-Content $hbFile | ConvertFrom-Json
        $age = [math]::Round(([DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $hb.ts))
        $s = $hb.stats
        Write-Host ""
        Write-Host "  BRIDGE CYCLE" -ForegroundColor White
        Write-Host "  Last: ${age}s ago | Patterns: $($s.pattern_processed) | LLM: $($s.llm_advisory)" -ForegroundColor Gray
    }

    $fbFile = "$env:USERPROFILE\.spark\feedback_state.json"
    if (Test-Path $fbFile) {
        $fb = Get-Content $fbFile | ConvertFrom-Json
        $rate = [math]::Round($fb.advice_action_rate * 100, 1)
        Write-Host ""
        Write-Host "  FEEDBACK LOOP" -ForegroundColor White
        Write-Host "  Processed: $($fb.total_processed) | Positive: $($fb.total_positive) | Action rate: ${rate}%" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "  ==========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Show-Health {
    Write-Host ""
    $issues = 0

    try { $null = Invoke-RestMethod http://127.0.0.1:8787/health -TimeoutSec 2; Write-Host "  [OK] sparkd :8787" -ForegroundColor Green }
    catch { Write-Host "  [!!] sparkd :8787" -ForegroundColor Red; $issues++ }

    $pc = curl.exe -s -o NUL -w "%{http_code}" --max-time 2 http://127.0.0.1:8765/ 2>$null
    if ($pc -eq "200") { Write-Host "  [OK] pulse  :8765" -ForegroundColor Green }
    else { Write-Host "  [!!] pulse  :8765 (HTTP $pc)" -ForegroundColor Red; $issues++ }

    $total = [math]::Round((Get-Process python -ErrorAction SilentlyContinue | Measure-Object -Property WorkingSet64 -Sum).Sum/1MB)
    if ($total -lt 500) { Write-Host "  [OK] RAM: ${total}MB" -ForegroundColor Green }
    else { Write-Host "  [!!] RAM: ${total}MB (high)" -ForegroundColor Yellow; $issues++ }

    if ($issues -eq 0) { Write-Host "`n  All healthy" -ForegroundColor Green }
    else { Write-Host "`n  $issues issue(s) found" -ForegroundColor Yellow }
    Write-Host ""
}

switch ($Action) {
    "start"   { Start-Spark }
    "stop"    { Stop-Spark }
    "status"  { Show-Status }
    "restart" { Stop-Spark; Start-Sleep 2; Start-Spark }
    "health"  { Show-Health }
}
