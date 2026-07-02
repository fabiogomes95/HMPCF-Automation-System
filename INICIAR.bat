@echo off
REM Launcher principal/manual: sobe Docker (Postgres) + backend + abre navegador.
REM Ver tambem scripts/windows/ABRIR_HMPCF.bat (launcher leve, sem Docker) e
REM scripts/windows/iniciar_sistema.vbs (usado por atalho/boot silencioso).
REM Nao remover nenhum dos tres sem antes confirmar no Agendador de Tarefas
REM do Windows (Task Scheduler) qual deles esta registrado para autostart.
chcp 65001 >nul
echo.
echo ==========================================
echo   HMPCF -- Sistema Hospitalar
echo ==========================================
echo.

REM ── 1. PostgreSQL via Docker ──────────────────────────────────────────────
echo [1/3] Verificando PostgreSQL...
docker start hmpcf_postgres >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Nao foi possivel iniciar o PostgreSQL.
    echo      Verifique se o Docker Desktop esta aberto.
    echo.
)
timeout /t 4 /nobreak >nul

REM ── 2. Backend FastAPI ───────────────────────────────────────────────────
echo [2/3] Iniciando backend...
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
    echo  [ERRO] Ambiente virtual nao encontrado em backend\.venv
    echo         Execute no PowerShell:
    echo           cd backend
    echo           python -m venv .venv
    echo           .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

start "HMPCF-Backend" /min .venv\Scripts\python.exe -m uvicorn app.main:app ^
    --host 0.0.0.0 ^
    --port 8001

timeout /t 5 /nobreak >nul

REM ── 3. Abrir navegador ────────────────────────────────────────────────────
echo [3/3] Abrindo HMPCF...
start http://localhost:8001

echo.
echo ==========================================
echo  Sistema iniciado!
echo.
echo  Acesso local : http://localhost:8001
echo  Acesso LAN   : http://%COMPUTERNAME%:8001
echo ==========================================
echo.
echo  Para encerrar: feche a janela minimizada
echo  "HMPCF-Backend" na barra de tarefas.
echo.
pause
