param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$SparkArgs
)

Write-Host "[deprecated] scripts/spark.ps1 is deprecated. Use: python -m spark.cli <command>" -ForegroundColor Yellow
python -m spark.cli @SparkArgs
exit $LASTEXITCODE
