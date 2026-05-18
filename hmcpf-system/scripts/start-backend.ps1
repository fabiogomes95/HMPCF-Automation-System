$rootDir = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $rootDir "backend"

Write-Host "[start] Iniciando backend (FastAPI) em nova janela..." -ForegroundColor Green
Start-Process powershell -WindowStyle Normal -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$backendDir'; python -m app.main"
)
