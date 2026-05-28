@echo off
chcp 65001 >nul
REM ──────────────────────────────────────────────────────────────────────────
REM Instala o backend HMPCF como servico Windows usando NSSM.
REM
REM Pre-requisitos:
REM   1. Baixe o NSSM em https://nssm.cc/download
REM   2. Extraia nssm.exe para C:\nssm\nssm.exe
REM   3. Execute este script como Administrador
REM ──────────────────────────────────────────────────────────────────────────

set NSSM=C:\nssm\nssm.exe
set SERVICE=HMPCF-Backend
set APP_DIR=%~dp0..\backend
set PYTHON=%~dp0..\backend\.venv\Scripts\python.exe
set LOG_DIR=C:\hmpcf-logs

REM ── Verificar NSSM ────────────────────────────────────────────────────────
if not exist "%NSSM%" (
    echo [ERRO] NSSM nao encontrado em %NSSM%
    echo.
    echo  1. Acesse: https://nssm.cc/download
    echo  2. Baixe a versao Win64
    echo  3. Extraia nssm.exe para C:\nssm\
    echo.
    pause
    exit /b 1
)

REM ── Verificar .venv ───────────────────────────────────────────────────────
if not exist "%PYTHON%" (
    echo [ERRO] Python do .venv nao encontrado: %PYTHON%
    pause
    exit /b 1
)

REM ── Criar pasta de logs ───────────────────────────────────────────────────
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM ── Remover servico anterior se existir ──────────────────────────────────
"%NSSM%" status %SERVICE% >nul 2>&1
if %errorlevel% equ 0 (
    echo Removendo servico anterior...
    "%NSSM%" stop %SERVICE% >nul 2>&1
    "%NSSM%" remove %SERVICE% confirm >nul 2>&1
)

REM ── Instalar servico ─────────────────────────────────────────────────────
echo Instalando servico %SERVICE%...

"%NSSM%" install %SERVICE% "%PYTHON%" "-m uvicorn app.main:app --host 0.0.0.0 --port 8001"
"%NSSM%" set %SERVICE% AppDirectory "%APP_DIR%"
"%NSSM%" set %SERVICE% DisplayName "HMPCF Backend"
"%NSSM%" set %SERVICE% Description "Sistema Hospitalar HMPCF — Backend FastAPI"
"%NSSM%" set %SERVICE% Start SERVICE_AUTO_START
"%NSSM%" set %SERVICE% AppStdout "%LOG_DIR%\backend.log"
"%NSSM%" set %SERVICE% AppStderr "%LOG_DIR%\backend_err.log"
"%NSSM%" set %SERVICE% AppRotateFiles 1
"%NSSM%" set %SERVICE% AppRotateBytes 10485760
"%NSSM%" set %SERVICE% AppRestartDelay 5000

REM ── Iniciar servico ───────────────────────────────────────────────────────
echo Iniciando servico...
"%NSSM%" start %SERVICE%

echo.
echo ==========================================
echo  Servico instalado com sucesso!
echo.
echo  Verificar:  sc query %SERVICE%
echo  Parar:      net stop %SERVICE%
echo  Iniciar:    net start %SERVICE%
echo  Remover:    %NSSM% remove %SERVICE% confirm
echo  Logs:       %LOG_DIR%\
echo ==========================================
echo.
pause
