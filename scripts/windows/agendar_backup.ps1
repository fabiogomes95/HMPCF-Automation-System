# Registra o backup diário do PostgreSQL no Agendador de Tarefas do Windows.
# Execute como Administrador:
#   powershell -ExecutionPolicy Bypass -File agendar_backup.ps1

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackupBat  = Join-Path $ScriptDir "backup_postgres.bat"
$TaskName   = "HMPCF-Backup-Diario"
$HorarioStr = "23:00"

if (-not (Test-Path $BackupBat)) {
    Write-Error "Nao encontrado: $BackupBat"
    exit 1
}

$action   = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$BackupBat`""
$trigger  = New-ScheduledTaskTrigger -Daily -At $HorarioStr
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false

Register-ScheduledTask `
    -TaskName   $TaskName `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -RunLevel   Highest `
    -Force | Out-Null

Write-Host "Backup diario agendado para $HorarioStr"
Write-Host "Backups criptografados salvos em: C:\HMPCF\backups\ (.sql.enc)"
Write-Host ""
Write-Host "Para verificar: Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "Para rodar agora: Start-ScheduledTask -TaskName '$TaskName'"
