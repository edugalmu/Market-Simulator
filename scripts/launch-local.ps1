Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot 'backend'

Set-Location $backendDir

$frontendDist = Join-Path $repoRoot 'frontend\dist'
if (-not (Test-Path $frontendDist)) {
  Write-Host 'No existe frontend/dist. Construyendo frontend...' -ForegroundColor Yellow
  Set-Location (Join-Path $repoRoot 'frontend')
  npm install
  npm run build
  Set-Location $backendDir
}

python -m pip install -e .[dev]

$env:MARKET_SIMULATOR_FRONTEND_DIST_DIR = $frontendDist

python -m app.launcher
