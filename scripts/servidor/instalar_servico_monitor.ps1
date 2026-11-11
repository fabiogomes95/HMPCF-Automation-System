# Instala/atualiza o servico HMPCF-Monitor-Svc (nssm): avisa no Telegram
# quando o sistema ou o banco caem e quando o backup atrasa (ver monitor.py).
# Antes, criar C:\HMPCF\telegram.env com TELEGRAM_TOKEN e TELEGRAM_CHAT.
# Rodar como administrador no servidor:
#   powershell -ExecutionPolicy Bypass -File scripts\servidor\instalar_servico_monitor.ps1
#
# So ASCII: o Windows PowerShell 5.1 le .ps1 sem BOM como ANSI.
$ErrorActionPreference = "Stop"
$raiz = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$nssm = Join-Path $raiz "nssm\nssm.exe"
$python = Join-Path $raiz "backend\.venv\Scripts\python.exe"
$script = Join-Path $PSScriptRoot "monitor.py"
$servico = "HMPCF-Monitor-Svc"
$log = "C:\HMPCF\monitor.log"

foreach ($f in @($nssm, $python, $script, "C:\HMPCF\telegram.env")) { if (-not (Test-Path $f)) { throw "Nao encontrado: $f" } }

if (Get-Service $servico -ErrorAction SilentlyContinue) {
    & $nssm stop $servico | Out-Null
} else {
    & $nssm install $servico $python | Out-Null
}
& $nssm set $servico Application $python | Out-Null
& $nssm set $servico AppParameters "`"$script`"" | Out-Null
& $nssm set $servico AppDirectory $PSScriptRoot | Out-Null
& $nssm set $servico DisplayName "HMPCF Monitor (avisos no Telegram)" | Out-Null
& $nssm set $servico Description "Avisa no Telegram se o sistema/banco cair ou o backup atrasar (scripts\servidor\monitor.py)" | Out-Null
& $nssm set $servico Start SERVICE_AUTO_START | Out-Null
& $nssm set $servico AppStdout $log | Out-Null
& $nssm set $servico AppStderr $log | Out-Null
& $nssm set $servico AppRotateFiles 1 | Out-Null
& $nssm set $servico AppRotateOnline 0 | Out-Null
& $nssm set $servico AppRotateBytes 1048576 | Out-Null
& $nssm set $servico AppEnvironmentExtra "PYTHONIOENCODING=utf-8" | Out-Null
& $nssm start $servico | Out-Null
Start-Sleep -Seconds 5
Write-Host "[OK] ${servico}: $((Get-Service $servico).Status)"
Get-Content $log -Tail 3
