param([string]$PromptFile, [string]$ResponseFile, [string]$SystemFile)
$p = Get-Content $PromptFile -Raw -Encoding UTF8
if ($SystemFile -and (Test-Path $SystemFile)) {
    $s = Get-Content $SystemFile -Raw -Encoding UTF8
    $r = claude -p --output-format text --append-system-prompt $s $p
} else {
    $r = claude -p --output-format text $p
}
Set-Content $ResponseFile -Value $r -Encoding UTF8
