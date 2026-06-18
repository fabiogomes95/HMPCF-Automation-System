@echo off
chcp 65001 >nul
echo.
echo ==========================================
echo   HMPCF -- Importar Planilha Junho 2026
echo ==========================================
echo.

set SCRIPT_DIR=%~dp0
set PYTHON=%SCRIPT_DIR%backend\.venv\Scripts\python.exe
set IMPORTADOR=%SCRIPT_DIR%scripts\importar_planilha_junho2026.py

if not exist "%PYTHON%" (
    echo [ERRO] Python do backend nao encontrado em:
    echo        %PYTHON%
    echo.
    echo Execute primeiro: cd backend e instale as dependencias.
    pause
    exit /b 1
)

if not exist "%IMPORTADOR%" (
    echo [ERRO] Script de importacao nao encontrado em:
    echo        %IMPORTADOR%
    pause
    exit /b 1
)

echo Iniciando importacao...
echo.
"%PYTHON%" "%IMPORTADOR%"

echo.
echo ==========================================
echo  Importacao concluida.
echo ==========================================
echo.
pause
