@echo off
set PGPASSWORD=hmpcf2026
set BACKUP_DIR=C:\HMPCF\backups
set DB=hmpcf
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
for /f "tokens=*" %%a in ('powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd'"') do set DATESTAMP=%%a
set OUTFILE=%BACKUP_DIR%\hmpcf_%DATESTAMP%.sql
echo Iniciando backup...
"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" -U postgres -h localhost -d %DB% -f "%OUTFILE%"
if %ERRORLEVEL% EQU 0 (echo [OK] Backup: %OUTFILE%) else (echo [ERRO] Falha no backup! & exit /b 1)
powershell -NoProfile -Command "Get-ChildItem '%BACKUP_DIR%' -Filter *.sql | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Force"
