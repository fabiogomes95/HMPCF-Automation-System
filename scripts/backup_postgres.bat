@echo off
chcp 65001 >nul

REM ── Configurações ─────────────────────────────────────────────────────────
set BACKUP_DIR=C:\hmpcf-backups
set DB_NAME=hmpcf
set DB_USER=postgres
set CONTAINER=hmpcf_postgres
set RETENCAO_DIAS=30

REM ── Data no formato YYYY-MM-DD ────────────────────────────────────────────
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set DT=%%a
set FILENAME=%BACKUP_DIR%\hmpcf_%DT%.sql

REM ── Criar diretório de backups se não existir ─────────────────────────────
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo [%date% %time%] Iniciando backup do banco %DB_NAME%...

REM ── Executar pg_dump dentro do container ─────────────────────────────────
docker exec %CONTAINER% pg_dump -U %DB_USER% %DB_NAME% > "%FILENAME%"

if %errorlevel% equ 0 (
    echo [OK] Backup salvo em: %FILENAME%
) else (
    echo [ERRO] Falha ao gerar backup!
    echo        Verifique se o container %CONTAINER% esta rodando.
    exit /b 1
)

REM ── Remover backups com mais de X dias ───────────────────────────────────
echo Removendo backups com mais de %RETENCAO_DIAS% dias...
forfiles /p "%BACKUP_DIR%" /s /m *.sql /d -%RETENCAO_DIAS% /c "cmd /c del @path" >nul 2>&1

echo [OK] Backup concluido.
