@echo off
title HMPCF — BPA Local
cd /d "%~dp0"

echo.
echo  =============================================
echo   HMPCF — BPA Local (modo offline)
echo  =============================================
echo.
echo  Iniciando Streamlit em http://localhost:8502
echo  Abrindo o navegador automaticamente...
echo.
echo  Para encerrar: feche esta janela ou Ctrl+C
echo.

.venv\Scripts\streamlit.exe run app.py ^
    --server.port 8502 ^
    --browser.gatherUsageStats false

pause
