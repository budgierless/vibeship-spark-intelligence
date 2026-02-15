param(
  [int]$Minutes = 10,
  [string]$SparkdBaseUrl = "http://127.0.0.1:8787",
  [string]$OutFile = "reports\\launch-readiness\\mission-1771186081212\\soak_health.log"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutFile) | Out-Null
Remove-Item -Force -ErrorAction SilentlyContinue $OutFile

$deadline = (Get-Date).AddMinutes($Minutes)

while ((Get-Date) -lt $deadline) {
  $ts = (Get-Date).ToString("o")
  try {
    # Invoke-WebRequest occasionally throws a NullReferenceException on some Windows setups.
    $health = (Invoke-RestMethod -Uri ($SparkdBaseUrl + "/health") -Method Get -TimeoutSec 5).ToString().Trim()
    $status = Invoke-RestMethod -Uri ($SparkdBaseUrl + "/status") -Method Get -TimeoutSec 5
    $line = "$ts ok health=$health bridge_ts=$($status.bridge_worker.last_heartbeat) pattern_backlog=$($status.bridge_worker.pattern_backlog)"
  } catch {
    $line = "$ts ERROR $($_.Exception.Message)"
  }

  Add-Content -Path $OutFile -Value $line -Encoding utf8
  Start-Sleep -Seconds 10
}

Write-Host \"Wrote soak log: $OutFile\"
