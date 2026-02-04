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

function Test-Port {
    param([int]$Port)
    try {
        return (Test-NetConnection -ComputerName 127.0.0.1 -Port $Port).TcpTestSucceeded
    } catch {
        return $false
    }
}

function Test-Mind {
    param([int]$Port)
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2
        return $resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300
    } catch {
        return $false
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

$mindExe = Get-MindExe
if (-not $mindExe) {
    Write-Warning "[mind] mind.exe not found; skipping Mind startup"
    exit 0
}

$env:MIND_TIER = "standard"

$pgPort = Get-EmbeddedPgPort
if ($pgPort -and (Test-Port -Port $pgPort)) {
    $env:MIND_DATABASE_URL = "postgresql://mind:mind@127.0.0.1:$pgPort/mind"
} else {
    if (Test-Path Env:MIND_DATABASE_URL) { Remove-Item Env:MIND_DATABASE_URL }
}

$logDir = Join-Path $env:USERPROFILE ".spark\\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$outLog = Join-Path $logDir "mind_out.log"
$errLog = Join-Path $logDir "mind_err.log"

Start-Process -FilePath $mindExe -ArgumentList @("serve", "--host", "127.0.0.1", "--port", $MindPort.ToString()) -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog

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
