param(
    [string]$ProjectPath = (Get-Location).Path
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptRoot "..")
$siblingPulse = Join-Path (Split-Path $repoRoot.Path -Parent) "vibeship-spark-pulse"

if (-not $env:SPARK_PULSE_DIR) {
    if (Test-Path (Join-Path $siblingPulse "app.py")) {
        $env:SPARK_PULSE_DIR = $siblingPulse
    } else {
        Write-Host "[warn] vibeship-spark-pulse not found. Set SPARK_PULSE_DIR env var."
    }
}

python -m spark.cli ensure --sync-context --project "$ProjectPath"
