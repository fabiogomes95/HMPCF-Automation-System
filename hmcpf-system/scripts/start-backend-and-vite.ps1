$rootDir = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"
$rustBin = Join-Path $env:USERPROFILE ".cargo\bin"

$env:Path = "$rustBin;$env:Path"

Write-Host "[start] Iniciando backend (FastAPI)..." -ForegroundColor Green
$bp = Start-Process powershell -WindowStyle Normal -PassThru -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$backendDir'; python -m app.main"
)
Write-Host "[start] Backend PID: $($bp.Id)" -ForegroundColor Green

Write-Host "[start] Aguardando backend..." -ForegroundColor Green
Start-Sleep -Seconds 4

Write-Host "[start] Iniciando frontend (Vite dev server)..." -ForegroundColor Green
$fp = Start-Process powershell -WindowStyle Hidden -PassThru -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$frontendDir'; npm run dev"
)
Write-Host "[start] Frontend PID: $($fp.Id)" -ForegroundColor Green
Write-Host "[start] Aguardando servidores..." -ForegroundColor Green
Start-Sleep -Seconds 6
