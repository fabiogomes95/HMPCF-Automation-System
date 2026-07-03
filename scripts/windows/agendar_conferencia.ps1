# Registra a conferencia semanal (digitado x lote de producao no Firebird) no
# Agendador de Tarefas do Windows, toda sexta-feira.
# Execute como Administrador:
#   powershell -ExecutionPolicy Bypass -File agendar_conferencia.ps1

$ScriptDir      = Split-Path -Parent $MyInvocation.MyCommand.Path
$ConferenciaBat = Join-Path $ScriptDir "..\..\bpa\conferencia_semanal.bat"
$TaskName       = "HMPCF-Conferencia-Semanal"
$HorarioStr     = "18:00"

if (-not (Test-Path $ConferenciaBat)) {
    Write-Error "Nao encontrado: $ConferenciaBat"
    exit 1
}

$action   = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$ConferenciaBat`""
$trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Friday -At $HorarioStr
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false

Register-ScheduledTask `
    -TaskName   $TaskName `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -RunLevel   Highest `
    -Force | Out-Null

Write-Host "Conferencia semanal agendada para toda sexta-feira as $HorarioStr"
Write-Host "Relatorios salvos em: bpa\conferencia_relatorios\ (CPF mascarado)"
Write-Host "O resultado completo (sem mascara) tambem fica disponivel a qualquer hora na aba 'Conferencia' do painel BPA (http://localhost:8503)."
Write-Host ""
Write-Host "Para verificar: Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "Para rodar agora: Start-ScheduledTask -TaskName '$TaskName'"
