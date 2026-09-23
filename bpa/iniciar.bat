@echo off
title HMPCF — BPA Digitacao
cd /d "%~dp0"

echo.
echo  =============================================
echo   HMPCF — BPA Digitacao (Flask)
echo  =============================================
echo.
echo  Carregando pacientes do Firebird...
echo  Acesse: http://localhost:8503
echo.
echo  Para encerrar: feche esta janela ou Ctrl+C
echo.

REM Com bpa\.venv (instalar.ps1): BPA novo em FastAPI (executar.py).
REM Sem ele: o app antigo (app.py) no dashboard\.venv -- nenhum notebook fica sem BPA na troca.
set "PY=%~dp0.venv\Scripts\python.exe"
set "APP=executar.py"
if not exist "%PY%" (
    set "PY=%~dp0..\dashboard\.venv\Scripts\python.exe"
    set "APP=app.py"
)
"%PY%" %APP%

pause
