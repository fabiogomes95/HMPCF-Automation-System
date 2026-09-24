@echo off
REM Toda execucao (manual ou agendada) vai pro log -- a tarefa agendada roda
REM sem janela, e sem isso uma falha passava despercebida (ficou de 17/06 a
REM 23/09/2026 sem backup nenhum porque a tarefa apontava pra um caminho antigo).
if not "%~1"=="--log" (
    if not exist "C:\HMPCF\backups" mkdir "C:\HMPCF\backups"
    call "%~f0" --log >> "C:\HMPCF\backups\backup.log" 2>&1
    exit /b %ERRORLEVEL%
)
echo.
echo ===== %DATE% %TIME% =====
for /f "tokens=1,* delims==" %%a in ('findstr /b "POSTGRES_PASSWORD=" "%~dp0..\..\backend\.env"') do set PGPASSWORD=%%b
if "%PGPASSWORD%"=="" (
    echo [ERRO] POSTGRES_PASSWORD nao encontrado em backend\.env
    exit /b 1
)
set BACKUP_DIR=C:\HMPCF\backups
set DB=hmpcf
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd'"') do set DATESTAMP=%%a
set OUTFILE=%BACKUP_DIR%\hmpcf_%DATESTAMP%.sql
echo Iniciando backup...
"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" -U postgres -h localhost -d %DB% -f "%OUTFILE%"
if %ERRORLEVEL% EQU 0 (echo [OK] Backup: %OUTFILE%) else (echo [ERRO] Falha no backup! & exit /b 1)

echo Criptografando backup...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0encrypt_backup.ps1" -Path "%OUTFILE%"
if %ERRORLEVEL% NEQ 0 (echo [ERRO] Falha ao criptografar o backup! & exit /b 1)

echo Copiando backup para fora da maquina (Google Drive)...
REM 1) Pasta local que o app do Google Drive sincroniza ("Pastas do computador").
REM    Funciona tambem pelo servico HMPCF-Backup-Svc (LocalSystem), que nao pode
REM    gravar no G: -- ver agendador_backup.py.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0copiar_backup_nuvem.ps1" -Path "%OUTFILE%.enc" -DestinoPasta "C:\HMPCF\backups_nuvem"
if %ERRORLEVEL% NEQ 0 (echo [AVISO] Copia externa falhou -- backup local OK, mas sem copia fora da maquina hoje.)
REM 2) Rodando como o usuario (dois cliques): copia direto no G: tambem, como antes.
if /i not "%USERNAME%"=="%COMPUTERNAME%$" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0copiar_backup_nuvem.ps1" -Path "%OUTFILE%.enc"
)

REM Expurgo: 30 dias, agora sobre os arquivos .enc (o .sql em claro ja foi apagado)
powershell -NoProfile -Command "Get-ChildItem '%BACKUP_DIR%' -Filter *.sql.enc | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Force"

REM Logs do backend ja trocados pelo nssm (a cada 10 MB, nssm_backend-<data>.log):
REM o nssm nunca apaga os antigos, entao o expurgo de 90 dias fica aqui.
powershell -NoProfile -Command "Get-ChildItem '%~dp0..\..\backend' -Filter 'nssm_backend-*.log' | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-90) } | Remove-Item -Force"
echo [OK] Fim do backup.
exit /b 0
