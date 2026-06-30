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

..\dashboard\.venv\Scripts\python.exe app.py

pause
