param(
  [string]$OutDir = "reports\\launch-readiness\\mission-1771186081212\\rc",
  [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

Push-Location (Split-Path -Parent $PSScriptRoot)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

if (-not $SkipBuild) {
  Write-Host "Building sdist + wheel..."
  python -m build
}

$dist = Join-Path (Get-Location) "dist"
if (!(Test-Path $dist)) { throw "dist/ not found after build" }

$files = Get-ChildItem $dist -File | Where-Object { $_.Name -match '\.(whl|tar\.gz)$' } | Sort-Object Name
if ($files.Count -eq 0) { throw "No build artifacts found in dist/" }

$manifest = [ordered]@{
  createdAt = (Get-Date).ToString("o")
  outDir = $OutDir
  artifacts = @()
}

foreach ($f in $files) {
  $hash = Get-FileHash -Algorithm SHA256 -Path $f.FullName
  $manifest.artifacts += [ordered]@{
    name = $f.Name
    bytes = $f.Length
    sha256 = $hash.Hash.ToLowerInvariant()
    path = $f.FullName
  }
}

$manifestPath = Join-Path $OutDir "rc_build_manifest.json"
$manifest | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 -Path $manifestPath

Write-Host "Wrote manifest:" $manifestPath

Pop-Location
