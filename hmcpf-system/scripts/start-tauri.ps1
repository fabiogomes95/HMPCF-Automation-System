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
Write-Host "[start] Backend PID: $($bp.Id) (janela separada)" -ForegroundColor Green

Write-Host "[start] Aguardando backend..." -ForegroundColor Green
Start-Sleep -Seconds 4

Write-Host "[start] Iniciando Tauri dev..." -ForegroundColor Green
Set-Location $frontendDir
npm run tauri:dev
