@echo off
cd /d "%~dp0"

set "LOG=%~dp0start_recepcao.log"
echo [%date% %time%] Iniciando Recepcao... > "%LOG%"

netstat -ano | findstr :8000 >nul
if %errorlevel% equ 0 (
    echo [!] Matando processo atual na porta 8000... >> "%LOG%"
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
        taskkill /f /pid %%a >nul 2>nul
    )
    timeout /t 2 /nobreak >nul
)

echo [!] Localizando Python... >> "%LOG%"
for /f "delims=" %%i in ('python -c "import sys; print(sys.executable)"' 2^>nul) do set "PY_PATH=%%i"
if not defined PY_PATH (
    for /f "delims=" %%i in ('where python 2^>nul') do set "PY_PATH=%%i"
)
if not defined PY_PATH (
    for /f "delims=" %%i in ('dir /s /b "%LOCALAPPDATA%\Programs\Python\*\python.exe" 2^>nul') do set "PY_PATH=%%i"
)
if not defined PY_PATH (
    echo [ERRO] Python nao encontrado >> "%LOG%"
    msg * "Python nao encontrado. Instale o Python 3.10+"
    exit
)

echo Python: %PY_PATH% >> "%LOG%"

set "PYW_PATH=%PY_PATH:python.exe=pythonw.exe%"
echo PYW: %PYW_PATH% >> "%LOG%"
echo Script: %~dp0app_recepcao.py >> "%LOG%"

if not exist "%PYW_PATH%" (
    echo [ERRO] pythonw.exe nao encontrado em %PYW_PATH% >> "%LOG%"
    msg * "pythonw.exe nao encontrado em %PYW_PATH%"
    exit
)

if not exist "%~dp0app_recepcao.py" (
    echo [ERRO] app_recepcao.py nao encontrado >> "%LOG%"
    msg * "app_recepcao.py nao encontrado em %~dp0"
    exit
)

echo [!] Iniciando Recepcao (porta 8000)... >> "%LOG%"
start "" "%PYW_PATH%" "%~dp0app_recepcao.py"
echo [OK] Processo iniciado! >> "%LOG%"
exit
