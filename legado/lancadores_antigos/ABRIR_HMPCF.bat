@echo off
REM Launcher leve (sem checar/subir Docker): so garante que o backend esta no
REM ar e abre o navegador. Ver tambem INICIAR.bat (raiz, launcher completo) e
REM iniciar_sistema.vbs (usado por atalho/boot silencioso). Nao remover sem
REM confirmar no Agendador de Tarefas do Windows qual esta registrado.
chcp 65001 >nul

REM ── Verifica se o backend ja esta rodando ──────────────────────────────────
netstat -an 2>nul | findstr ":8001" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 goto :abrir_navegador

REM ── Nao esta rodando — inicia o backend ───────────────────────────────────
echo Iniciando HMPCF, aguarde...
start "" /min "C:\HMPCF-Automation-System\backend\.venv\Scripts\uvicorn.exe" ^
    app.main:app --host 0.0.0.0 --port 8001 ^
    --app-dir "C:\HMPCF-Automation-System\backend"

REM ── Aguarda o backend subir (ate 20s) ─────────────────────────────────────
set /a tentativa=0
:aguardar
set /a tentativa+=1
timeout /t 2 /nobreak >nul
netstat -an 2>nul | findstr ":8001" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 goto :abrir_navegador
if %tentativa% lss 10 goto :aguardar

echo [ERRO] Nao foi possivel iniciar o backend. Contate o suporte.
pause
exit /b 1

:abrir_navegador
start "" http://localhost:8001
exit /b 0
