@echo off
cd /d "%~dp0"

set "LOG=%~dp0start_bpa.log"
echo [%date% %time%] Iniciando BPA... > "%LOG%"

netstat -ano | findstr :8503 >nul
if %errorlevel% equ 0 (
    echo Ja esta rodando na porta 8503, so abre o navegador. >> "%LOG%"
) else (
    echo Iniciando servidor Flask na porta 8503... >> "%LOG%"
    start "" /min "..\dashboard\.venv\Scripts\pythonw.exe" "app.py"
    ping -n 13 127.0.0.1 >nul
)

start "" "http://localhost:8503"
exit
