# Instala/atualiza o BPA neste notebook (rodar de novo = atualizar).
#   1. Python proprio em bpa\.venv (sem depender de dashboard\.venv)
#   2. bpa\.env com as credenciais do Firebird (copiadas de dashboard\.env, se faltarem)
#   3. Tarefa Agendada "HMPCF-BPA": liga o BPA sozinho ao entrar no Windows
#
# Uso (PowerShell, na pasta do repositorio):
#   powershell -ExecutionPolicy Bypass -File bpa\instalar.ps1
#
# So ASCII nas strings: o Windows PowerShell 5.1 le .ps1 sem BOM como ANSI.
$ErrorActionPreference = "Stop"
$bpa = $PSScriptRoot
$venv = Join-Path $bpa ".venv"
$envBpa = Join-Path $bpa ".env"
$envDash = Join-Path (Split-Path $bpa -Parent) "dashboard\.env"
$tarefa = "HMPCF-BPA"

function Passo($t) { Write-Host ""; Write-Host "== $t" -ForegroundColor Cyan }

# 1. Python proprio -------------------------------------------------------------
Passo "Ambiente Python do BPA"
if (-not (Test-Path (Join-Path $venv "Scripts\python.exe"))) {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { & py -3 -m venv $venv } else { & python -m venv $venv }
    if ($LASTEXITCODE -ne 0) { throw "Nao consegui criar o venv (Python instalado?)" }
    Write-Host "[OK] Criado: $venv"
} else {
    Write-Host "[OK] Ja existe: $venv"
}
& (Join-Path $venv "Scripts\python.exe") -m pip install -q --disable-pip-version-check -r (Join-Path $bpa "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install falhou" }
Write-Host "[OK] Dependencias instaladas/atualizadas"

# 2. .env ------------------------------------------------------------------------
Passo "Configuracao (bpa\.env)"
$linhasBpa = @()
if (Test-Path $envBpa) { $linhasBpa = @(Get-Content $envBpa) }
$faltando = @("FIREBIRD_PATH", "FIREBIRD_USER", "FIREBIRD_PASSWORD") |
    Where-Object { $chave = $_; -not ($linhasBpa | Where-Object { $_ -match "^$chave=" }) }
if ($faltando -and (Test-Path $envDash)) {
    if (Test-Path $envBpa) { Copy-Item $envBpa "$envBpa.bak_$(Get-Date -Format yyyyMMdd_HHmmss)" }
    $copiar = Get-Content $envDash | Where-Object { $l = $_; $faltando | Where-Object { $l -match "^$_=" } }
    Add-Content -Path $envBpa -Value (@("", "# Copiado de dashboard\.env pelo instalar.ps1") + $copiar) -Encoding ASCII
    Write-Host "[OK] Copiado de dashboard\.env: $($faltando -join ', ') (valores nao exibidos)"
} elseif ($faltando) {
    Write-Host "[AVISO] Faltam em bpa\.env: $($faltando -join ', ') -- preencha a mao (ver .env.example)" -ForegroundColor Yellow
} else {
    Write-Host "[OK] bpa\.env ja tem as credenciais do Firebird"
}

# 3. Ligar com o Windows -------------------------------------------------------
Passo "Iniciar com o Windows (tarefa $tarefa)"
$acao = New-ScheduledTaskAction -Execute (Join-Path $venv "Scripts\pythonw.exe") -Argument "app.py" -WorkingDirectory $bpa
$gatilho = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
# Espera o Firebird subir depois do logon antes de carregar os pacientes.
$gatilho.Delay = "PT30S"
$config = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable
Register-ScheduledTask -TaskName $tarefa -Action $acao -Trigger $gatilho -Settings $config `
    -Description "BPA HMPCF local (porta 8503) - Firebird/BPA Magnetico deste notebook" -Force | Out-Null
Write-Host "[OK] Tarefa registrada para o usuario $env:USERNAME"

# Liga agora, se ainda nao estiver rodando
$rodando = Get-NetTCPConnection -LocalPort 8503 -State Listen -ErrorAction SilentlyContinue
if ($rodando) {
    Write-Host "[OK] BPA ja estava rodando na porta 8503 (reinicie o Windows ou feche o BPA para usar o Python novo)"
} else {
    Start-ScheduledTask -TaskName $tarefa
    Write-Host "[OK] BPA iniciado -- abra http://localhost:8503 em alguns segundos"
}
Write-Host ""
Write-Host "Pronto." -ForegroundColor Green
