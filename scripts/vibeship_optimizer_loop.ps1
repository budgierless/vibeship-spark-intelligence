param(
  [Parameter(Mandatory=$true)]
  [ValidateSet("start","finish")]
  [string]$Phase,

  [string]$Title = "",
  [string]$ChangeId = "",
  [int]$Rounds = 80
)

$ErrorActionPreference = "Stop"

function Invoke-VO {
  param([string[]]$Args)
  & python -m vibeship_optimizer @Args
  if ($LASTEXITCODE -ne 0) { throw "vibeship-optimizer failed: $($Args -join ' ')" }
}

function Ensure-Dir([string]$Path) {
  if (!(Test-Path $Path)) { New-Item -ItemType Directory -Force $Path | Out-Null }
}

Ensure-Dir "reports/optimizer"

Invoke-VO @("init","--no-prompt")

if ($Phase -eq "start") {
  if (-not $Title) { throw "Phase=start requires -Title" }

  if (-not $ChangeId) {
    $raw = & python -m vibeship_optimizer change start --title $Title
    if ($LASTEXITCODE -ne 0) { throw "change start failed" }
    $obj = $raw | ConvertFrom-Json
    $ChangeId = [string]$obj.change_id
  }

  $preflightOut = "reports/optimizer/$ChangeId`_preflight.md"
  Invoke-VO @("preflight","--change-id",$ChangeId,"--out",$preflightOut)

  $beforeSnap = & python -m vibeship_optimizer snapshot --label before --change-id $ChangeId --as before
  if ($LASTEXITCODE -ne 0) { throw "snapshot(before) failed" }
  $beforeSnap = ($beforeSnap | Select-Object -Last 1).Trim()
  Set-Content -Encoding ascii -Path "reports/optimizer/$ChangeId`_before.path" -Value $beforeSnap

  Write-Host ("change_id=" + $ChangeId)
  Write-Host ("before_snapshot=" + $beforeSnap)
  Write-Host ("next=make one optimization commit, then run: .\\scripts\\vibeship_optimizer_loop.ps1 -Phase finish -ChangeId " + $ChangeId)
  exit 0
}

if ($Phase -eq "finish") {
  if (-not $ChangeId) { throw "Phase=finish requires -ChangeId" }

  $beforePathFile = "reports/optimizer/$ChangeId`_before.path"
  if (!(Test-Path $beforePathFile)) { throw "Missing $beforePathFile (run Phase=start first)" }
  $beforeSnap = (Get-Content $beforePathFile -Raw).Trim()
  if (-not $beforeSnap) { throw "Empty before snapshot path in $beforePathFile" }

  $afterSnap = & python -m vibeship_optimizer snapshot --label after --change-id $ChangeId --as after
  if ($LASTEXITCODE -ne 0) { throw "snapshot(after) failed" }
  $afterSnap = ($afterSnap | Select-Object -Last 1).Trim()
  Set-Content -Encoding ascii -Path "reports/optimizer/$ChangeId`_after.path" -Value $afterSnap

  $cmpMd = "reports/optimizer/$ChangeId`_compare.md"
  $cmpJson = "reports/optimizer/$ChangeId`_compare.json"
  Invoke-VO @("compare","--before",$beforeSnap,"--after",$afterSnap,"--out",$cmpMd,"--json-out",$cmpJson)

  # Spark critical-path KPI capture (advisory speed + delivery).
  $deltaOut = "reports/optimizer/$ChangeId`_advisory_delta.json"
  & python scripts/advisory_controlled_delta.py --rounds $Rounds --label $ChangeId --force-live --out $deltaOut | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "advisory_controlled_delta failed" }

  Write-Host ("change_id=" + $ChangeId)
  Write-Host ("after_snapshot=" + $afterSnap)
  Write-Host ("compare_md=" + $cmpMd)
  Write-Host ("advisory_delta=" + $deltaOut)
  exit 0
}

throw "Unknown -Phase: $Phase"

