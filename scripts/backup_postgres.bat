@echo off
chcp 65001 >nul

REM ── Configurações ─────────────────────────────────────────────────────────
set BACKUP_DIR=C:\hmpcf-backups
set DB_NAME=hmpcf
set DB_USER=postgres
set DB_HOST=localhost
set DB_PORT=5432
set PG_DUMP="C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"
set RETENCAO_DIAS=30

REM ── Senha via variável de ambiente (evita prompt) ─────────────────────────
REM  Defina PGPASSWORD no ambiente do sistema ou neste script:
REM  set PGPASSWORD=sua_senha_aqui
if not defined PGPASSWORD (
    echo [AVISO] PGPASSWORD nao definida. O backup pode pedir senha interativa.
)

REM ── Data no formato YYYY-MM-DD ────────────────────────────────────────────
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set DT=%%a
set FILENAME=%BACKUP_DIR%\hmpcf_%DT%.sql

REM ── Criar diretório se não existir ───────────────────────────────────────
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo [%date% %time%] Iniciando backup do banco %DB_NAME%...

REM ── Executar pg_dump nativo ───────────────────────────────────────────────
%PG_DUMP% -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -F p %DB_NAME% > "%FILENAME%"

if %errorlevel% equ 0 (
    echo [OK] Backup salvo em: %FILENAME%
) else (
    echo [ERRO] Falha ao gerar backup! Verifique as credenciais e o servico PostgreSQL.
    del "%FILENAME%" >nul 2>&1
    exit /b 1
)

REM ── Remover backups com mais de X dias ───────────────────────────────────
forfiles /p "%BACKUP_DIR%" /s /m *.sql /d -%RETENCAO_DIAS% /c "cmd /c del @path" >nul 2>&1

echo [OK] Backup concluido: %FILENAME%
