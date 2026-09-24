# Instala/atualiza o servico HMPCF-Backup-Svc (nssm): backup diario do banco
# as 23:00 sem depender do Agendador de Tarefas do Windows (ver
# agendador_backup.py). Rodar como administrador no servidor:
#   powershell -ExecutionPolicy Bypass -File scripts\servidor\instalar_servico_backup.ps1
#
# So ASCII: o Windows PowerShell 5.1 le .ps1 sem BOM como ANSI.
$ErrorActionPreference = "Stop"
$raiz = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$nssm = Join-Path $raiz "nssm\nssm.exe"
$python = Join-Path $raiz "backend\.venv\Scripts\python.exe"
$script = Join-Path $PSScriptRoot "agendador_backup.py"
$servico = "HMPCF-Backup-Svc"
$logs = "C:\HMPCF\backups"

foreach ($f in @($nssm, $python, $script)) { if (-not (Test-Path $f)) { throw "Nao encontrado: $f" } }
New-Item -ItemType Directory -Force -Path $logs, "C:\HMPCF\backups_nuvem" | Out-Null

if (Get-Service $servico -ErrorAction SilentlyContinue) {
    & $nssm stop $servico | Out-Null
} else {
    & $nssm install $servico $python | Out-Null
}
& $nssm set $servico Application $python | Out-Null
& $nssm set $servico AppParameters "`"$script`"" | Out-Null
& $nssm set $servico AppDirectory $PSScriptRoot | Out-Null
& $nssm set $servico DisplayName "HMPCF Backup diario (23:00)" | Out-Null
& $nssm set $servico Description "Backup do banco hmpcf todo dia as 23:00 (scripts\servidor\agendador_backup.py)" | Out-Null
& $nssm set $servico Start SERVICE_AUTO_START | Out-Null
& $nssm set $servico AppStdout (Join-Path $logs "agendador_backup.log") | Out-Null
& $nssm set $servico AppStderr (Join-Path $logs "agendador_backup.log") | Out-Null
& $nssm set $servico AppRotateFiles 1 | Out-Null
& $nssm set $servico AppRotateOnline 0 | Out-Null
& $nssm set $servico AppRotateBytes 1048576 | Out-Null
& $nssm set $servico AppEnvironmentExtra "PYTHONIOENCODING=utf-8" | Out-Null
& $nssm start $servico | Out-Null
Start-Sleep -Seconds 3
Write-Host "[OK] ${servico}: $((Get-Service $servico).Status)"
Get-Content (Join-Path $logs "agendador_backup.log") -Tail 3
