param(
    [int]$MindPort = 8080,
    [int]$MaxWaitSeconds = 60
)

$ErrorActionPreference = "SilentlyContinue"

function Get-MindExe {
    $cmd = Get-Command mind -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    $candidates = @(
        (Join-Path $env:APPDATA "Python\\Python313\\Scripts\\mind.exe"),
        (Join-Path $env:APPDATA "Python\\Python312\\Scripts\\mind.exe"),
        (Join-Path $env:USERPROFILE ".local\\bin\\mind.exe")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

function Test-TruthyEnv {
    param([string]$Value)
    if (-not $Value) { return $false }
    $v = $Value.ToLower().Trim()
    return @("1","true","yes","on") -contains $v
}

function Test-MindServe {
    param([string]$Exe)
    try {
        $out = & $Exe --help 2>&1
        return ($out -match "serve")
    } catch {
        return $false
    }
}

function Test-MindModule {
    param([string]$Module)
    try {
        $null = & python -c "import $Module" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Test-Port {
    param([int]$Port)
    try {
        return (Test-NetConnection -ComputerName 127.0.0.1 -Port $Port).TcpTestSucceeded
    } catch {
        return $false
    }
}

function Test-MindProcess {
    # Check if a Mind process is already running (backup check)
    $procs = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -match "lite_tier|mind_server|mind\.serve"
    }
    return ($procs.Count -gt 0)
}

function Test-Mind {
    param([int]$Port)
    try {
        # Increased timeout from 2s to 10s - Mind has cold start latency of 4-6s
        $resp = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 10
        return $resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300
    } catch {
        # Health check failed, but check if process exists (might just be slow)
        return Test-MindProcess
    }
}

function Get-EmbeddedPgPort {
    $pidFile = Join-Path $env:USERPROFILE ".mind\\data\\postgres\\postmaster.pid"
    if (-not (Test-Path $pidFile)) { return $null }
    try {
        $lines = Get-Content $pidFile
        if ($lines.Count -ge 4) {
            return [int]$lines[3].Trim()
        }
    } catch {
        return $null
    }
    return $null
}

if (Test-Mind -Port $MindPort) {
    Write-Host "[mind] already running on port $MindPort"
    exit 0
}

$forceBuiltin = Test-TruthyEnv $env:SPARK_FORCE_BUILTIN_MIND

$mindExe = Get-MindExe
if (-not $mindExe) {
    $mindExe = $null
}

$env:MIND_TIER = "standard"
$env:SPARK_MIND_PORT = $MindPort

$pgPort = Get-EmbeddedPgPort
if ($pgPort -and (Test-Port -Port $pgPort)) {
    # Local/dev fallback only; production should set MIND_DATABASE_URL explicitly.
    $env:MIND_DATABASE_URL = "postgresql://mind:mind@127.0.0.1:$pgPort/mind"
} else {
    if (Test-Path Env:MIND_DATABASE_URL) { Remove-Item Env:MIND_DATABASE_URL }
}

$logDir = Join-Path $env:USERPROFILE ".spark\\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$outLog = Join-Path $logDir "mind_out.log"
$errLog = Join-Path $logDir "mind_err.log"

if ($forceBuiltin) {
    $mindServer = Resolve-Path (Join-Path $PSScriptRoot "..\\mind_server.py")
    Start-Process -FilePath "python" -ArgumentList @($mindServer.Path) -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog
} elseif ($mindExe -and (Test-MindServe -Exe $mindExe)) {
    Start-Process -FilePath $mindExe -ArgumentList @("serve", "--host", "127.0.0.1", "--port", $MindPort.ToString()) -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog
} elseif (Test-MindModule -Module "mind.lite_tier") {
    Start-Process -FilePath "python" -ArgumentList @("-m", "mind.lite_tier") -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog
} else {
    $mindServer = Resolve-Path (Join-Path $PSScriptRoot "..\\mind_server.py")
    Start-Process -FilePath "python" -ArgumentList @($mindServer.Path) -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog
}

$deadline = (Get-Date).AddSeconds($MaxWaitSeconds)
while ((Get-Date) -lt $deadline) {
    if (Test-Mind -Port $MindPort) {
        Write-Host "[mind] running on port $MindPort"
        exit 0
    }
    Start-Sleep -Seconds 2
}

Write-Warning "[mind] not healthy after $MaxWaitSeconds seconds. Check logs: $outLog / $errLog"
exit 1
