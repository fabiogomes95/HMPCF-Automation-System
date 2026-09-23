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

REM Python do BPA: bpa\.venv (instalar.ps1); enquanto nao instalado, o antigo dashboard\.venv.
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=%~dp0..\dashboard\.venv\Scripts\python.exe"
"%PY%" app.py

pause
