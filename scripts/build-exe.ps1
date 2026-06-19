Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot 'backend'
$frontendDir = Join-Path $repoRoot 'frontend'
$frontendDist = Join-Path $frontendDir 'dist'
$releaseDir = Join-Path $repoRoot 'release'

Set-Location $frontendDir
npm install
npm run build

Set-Location $backendDir
python -m pip install -e .[dev]
python -m pip install pyinstaller

if (Test-Path $releaseDir) {
  Remove-Item $releaseDir -Recurse -Force
}
New-Item -ItemType Directory -Path $releaseDir | Out-Null

$sep = [System.IO.Path]::PathSeparator
$distMapping = "$frontendDist${sep}frontend/dist"

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name MarketSimulator `
  --distpath $releaseDir `
  --add-data $distMapping `
  app/launcher.py

Write-Host ''
Write-Host 'EXE generado en:' -ForegroundColor Green
Write-Host (Join-Path $releaseDir 'MarketSimulator.exe')
