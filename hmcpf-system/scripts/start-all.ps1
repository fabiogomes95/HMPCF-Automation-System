$rootDir = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"

Write-Host "[start] Iniciando backend (FastAPI)..." -ForegroundColor Green
$bp = Start-Process powershell -WindowStyle Hidden -PassThru -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$backendDir'; python -m app.main"
)
Write-Host "[start] Backend PID: $($bp.Id)" -ForegroundColor Green

Start-Sleep -Seconds 4

Write-Host "[start] Iniciando frontend (Vite)..." -ForegroundColor Green
$fp = Start-Process powershell -WindowStyle Hidden -PassThru -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$frontendDir'; npm run dev"
)
Write-Host "[start] Frontend PID: $($fp.Id)" -ForegroundColor Green

Start-Sleep -Seconds 6

Write-Host "[start] Iniciando Tauri Desktop..." -ForegroundColor Green
$tp = Start-Process powershell -WindowStyle Normal -PassThru -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$frontendDir'; npx tauri dev"
)
Write-Host "[start] Tauri PID: $($tp.Id)" -ForegroundColor Green

Write-Host "[start] TUDO PRONTO!" -ForegroundColor Green
Write-Host "  Backend : http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "  Tauri   : Janela Desktop nativa" -ForegroundColor Cyan
