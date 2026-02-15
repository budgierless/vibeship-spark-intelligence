param(
  [string]$SparkdUrl = "http://127.0.0.1:8787"
)

$ErrorActionPreference = "Stop"

Write-Host ("Sparkd health: {0}/health" -f $SparkdUrl)
$res = Invoke-RestMethod -Uri ("{0}/health" -f $SparkdUrl) -Method Get -TimeoutSec 5
$res | ConvertTo-Json -Depth 8

