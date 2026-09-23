@echo off
cd /d "%~dp0"
REM Com bpa\.venv (instalar.ps1): BPA novo em FastAPI (executar.py).
REM Sem ele: o app antigo (app.py) no dashboard\.venv -- nenhum notebook fica sem BPA na troca.
set "PY=%~dp0.venv\Scripts\pythonw.exe"
set "APP=executar.py"
if not exist "%PY%" (
    set "PY=%~dp0..\dashboard\.venv\Scripts\pythonw.exe"
    set "APP=app.py"
)

set "LOG=%~dp0start_bpa.log"
echo [%date% %time%] Iniciando BPA... > "%LOG%"

netstat -ano | findstr :8503 >nul
if %errorlevel% equ 0 (
    echo Ja esta rodando na porta 8503, so abre o navegador. >> "%LOG%"
) else (
    echo Iniciando BPA (%APP%) na porta 8503... >> "%LOG%"
    start "" /min "%PY%" "%APP%"
    ping -n 13 127.0.0.1 >nul
)

start "" "http://localhost:8503"
exit
