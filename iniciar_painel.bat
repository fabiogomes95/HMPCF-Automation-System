@echo off
cd /d "%~dp0"

netstat -ano | findstr :8001 >nul
if %errorlevel% equ 0 (
    echo [OK] Painel ja esta rodando. Abrindo interface...
    start msedge http://localhost:8001
    exit
)

echo [!] Localizando Python...
for /f "delims=" %%i in ('python -c "import sys; print(sys.executable)"' 2^>nul) do set "PY_PATH=%%i"
if not defined PY_PATH (
    for /f "delims=" %%i in ('where python 2^>nul') do set "PY_PATH=%%i"
)
if not defined PY_PATH (
    for /f "delims=" %%i in ('dir /s /b "%LOCALAPPDATA%\Programs\Python\*\python.exe" 2^>nul') do set "PY_PATH=%%i"
)
if not defined PY_PATH (
    msg * "Python nao encontrado. Instale o Python 3.10+"
    exit
)

set "PYW_PATH=%PY_PATH:python.exe=pythonw.exe%"
echo [!] Iniciando Painel de Gestao (porta 8001)...
start "" "%PYW_PATH%" app_painel.py
exit
