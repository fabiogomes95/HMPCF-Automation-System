@echo off
cd /d "%~dp0hmcpf-system\backend"
start /min python -m uvicorn app.main:app --reload --port 8000
timeout /t 4 /nobreak >nul

cd /d "%~dp0hmcpf-system\frontend"
start powershell -NoExit "npm run dev"
timeout /t 5 /nobreak >nul

start http://localhost:5173
echo.
echo ✅ HMPCF iniciado!
echo    Backend: http://localhost:8000
echo    Frontend: http://localhost:5173
echo.
echo ⚠️  Feche esta janela para parar o frontend (navegador continua)
echo    Para parar TUDO: feche o terminal do backend (minimizado na barra)
