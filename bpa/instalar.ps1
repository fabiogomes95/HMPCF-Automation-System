# Instala/atualiza o BPA neste notebook (rodar de novo = atualizar).
#   1. Python proprio em bpa\.venv (sem depender de dashboard\.venv)
#   2. bpa\.env com as credenciais do Firebird (copiadas de dashboard\.env, se faltarem)
#   3. Tarefa Agendada "HMPCF-BPA": liga o BPA sozinho ao entrar no Windows
#   4. Atalho "HMPCF - BPA" na area de trabalho (abre o sistema no Chrome)
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
# Tudo que o BPA usa passa a morar em bpa\.env: o que faltar e existir no
# dashboard\.env antigo e copiado (inclusive a PASTA DOS LOTES), pra pasta
# dashboard poder ser apagada sem o BPA mudar de lugar sem avisar.
Passo "Configuracao (bpa\.env)"
$chaves = @("FIREBIRD_PATH", "FIREBIRD_USER", "FIREBIRD_PASSWORD", "BPA_LOTES_DIR", "BPA_SAIDA_DIR",
            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")
$linhasBpa = @()
if (Test-Path $envBpa) { $linhasBpa = @(Get-Content $envBpa) }
$faltando = $chaves | Where-Object { $chave = $_; -not ($linhasBpa | Where-Object { $_ -match "^$chave=" }) }
$copiar = @()
if ($faltando -and (Test-Path $envDash)) {
    $copiar = @(Get-Content $envDash | Where-Object { $l = $_; $faltando | Where-Object { $l -match "^$_=" } })
}
if ($copiar.Count -gt 0) {
    if (Test-Path $envBpa) { Copy-Item $envBpa "$envBpa.bak_$(Get-Date -Format yyyyMMdd_HHmmss)" }
    Add-Content -Path $envBpa -Value (@("", "# Copiado de dashboard\.env pelo instalar.ps1") + $copiar) -Encoding ASCII
    $nomes = $copiar | ForEach-Object { ($_ -split "=", 2)[0] }
    Write-Host "[OK] Copiado de dashboard\.env: $($nomes -join ', ') (valores nao exibidos)"
    $linhasBpa = @(Get-Content $envBpa)
}
foreach ($c in @("FIREBIRD_PATH", "FIREBIRD_USER", "FIREBIRD_PASSWORD")) {
    if (-not ($linhasBpa | Where-Object { $_ -match "^$c=" })) {
        Write-Host "[AVISO] Falta $c em bpa\.env -- preencha a mao (ver .env.example)" -ForegroundColor Yellow
    }
}
$linhaLotes = $linhasBpa | Where-Object { $_ -match "^BPA_LOTES_DIR=" } | Select-Object -Last 1
if ($linhaLotes) {
    $pastaLotes = ($linhaLotes -split "=", 2)[1].Trim().Trim('"')
} elseif (Test-Path "C:\BPA") {
    $pastaLotes = "C:\BPA\bpa_lotes"   # mesmo padrao do bpa_local\config.py
} else {
    $pastaLotes = Join-Path $bpa "bpa_lotes"
    Write-Host "[AVISO] BPA_LOTES_DIR nao definido em bpa\.env -- lotes em $pastaLotes" -ForegroundColor Yellow
}
$qtd = @(Get-ChildItem $pastaLotes -Filter "??-??-????.txt" -ErrorAction SilentlyContinue).Count
Write-Host "[OK] Pasta dos lotes: $pastaLotes ($qtd lote(s) de dia)"

# 3. Ligar com o Windows -------------------------------------------------------
Passo "Iniciar com o Windows (tarefa $tarefa)"
$acao = New-ScheduledTaskAction -Execute (Join-Path $venv "Scripts\pythonw.exe") -Argument "executar.py" -WorkingDirectory $bpa
$gatilho = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
# Espera o Firebird subir depois do logon antes de carregar os pacientes.
$gatilho.Delay = "PT30S"
$config = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable
try {
    Register-ScheduledTask -TaskName $tarefa -Action $acao -Trigger $gatilho -Settings $config `
        -Description "BPA HMPCF local (porta 8503) - Firebird/BPA Magnetico deste notebook" -Force -ErrorAction Stop | Out-Null
    Write-Host "[OK] Tarefa registrada para o usuario $env:USERNAME"
} catch {
    # Tarefa criada antes num terminal de administrador: sem admin nao da pra
    # regravar, mas ela continua valendo -- so atualizar o BPA nao precisa disso.
    if (Get-ScheduledTask -TaskName $tarefa -ErrorAction SilentlyContinue) {
        Write-Host "[OK] Tarefa ja existe (sem permissao para regravar, mantida como esta)"
    } else {
        Write-Host "[AVISO] Nao consegui criar a tarefa: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "        Rode este instalar.ps1 uma vez como administrador." -ForegroundColor Yellow
    }
}

# (Re)liga agora: fecha o BPA que estiver na porta 8503 (antigo app.py ou o
# novo executar.py) e sobe pela tarefa -- assim rodar de novo = atualizar.
$rodando = Get-NetTCPConnection -LocalPort 8503 -State Listen -ErrorAction SilentlyContinue
if ($rodando) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($rodando[0].OwningProcess)"
    if ($proc.CommandLine -match "app\.py|executar\.py") {
        Stop-Process -Id $proc.ProcessId -Force
        Start-Sleep -Seconds 2
        Write-Host "[OK] BPA que estava rodando foi fechado para reiniciar"
    } else {
        Write-Host "[AVISO] Outro programa usa a porta 8503: $($proc.CommandLine)" -ForegroundColor Yellow
    }
}
try {
    Start-ScheduledTask -TaskName $tarefa -ErrorAction Stop
} catch {
    # Sem a tarefa (ou sem permissao nela): sobe direto, igual a tarefa faria
    Start-Process -FilePath (Join-Path $venv "Scripts\pythonw.exe") -ArgumentList "executar.py" -WorkingDirectory $bpa
}
Write-Host "[OK] BPA iniciado -- abra http://localhost:8503/ui/ em alguns segundos"
# 4. Atalho na area de trabalho --------------------------------------------------
# "HMPCF - BPA": abre o sistema do hospital direto no Chrome (sem janela preta),
# com o icone do robo. Tira os atalhos antigos que ligavam o BPA Flask a mao.
Passo "Atalho na area de trabalho"
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell
Get-ChildItem $desktop -Filter *.lnk -ErrorAction SilentlyContinue | ForEach-Object {
    $alvo = $shell.CreateShortcut($_.FullName)
    if ("$($alvo.TargetPath) $($alvo.Arguments)" -match "start_bpa\.vbs|iniciar_bpa_silencioso\.bat|bpa\\app\.py") {
        Remove-Item $_.FullName -Force
        Write-Host "[OK] Atalho antigo removido: $($_.Name)"
    }
}
$chrome = @(
    (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"),
    (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe")
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
$url = "http://192.168.1.29:8001"
$lnk = $shell.CreateShortcut((Join-Path $desktop "HMPCF - BPA.lnk"))
if ($chrome) {
    $lnk.TargetPath = $chrome
    $lnk.Arguments = $url
} else {
    # Sem Chrome: abre no navegador padrao
    $lnk.TargetPath = Join-Path $env:WINDIR "explorer.exe"
    $lnk.Arguments = $url
    Write-Host "[AVISO] Chrome nao encontrado -- o atalho abre no navegador padrao" -ForegroundColor Yellow
}
$lnk.IconLocation = (Join-Path $bpa "robo-icon.ico") + ",0"
$lnk.Description = "Sistema HMPCF (aba BPA) - $url"
$lnk.Save()
Write-Host "[OK] Atalho 'HMPCF - BPA' na area de trabalho"

Write-Host ""
Write-Host "Pronto." -ForegroundColor Green
