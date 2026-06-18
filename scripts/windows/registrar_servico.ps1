#Requires -RunAsAdministrator

$taskName = "HMPCF-Backend"
$uvicorn  = "C:\HMPCF-Automation-System\backend\.venv\Scripts\uvicorn.exe"
$args     = "app.main:app --host 0.0.0.0 --port 8001"
$workDir  = "C:\HMPCF-Automation-System\backend"
$logDir   = "C:\HMPCF-Automation-System\logs"
$watcher  = "C:\HMPCF-Automation-System\scripts\watchdog_backend.ps1"

# Garante pasta de logs
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

# ── 1. Tarefa principal: inicia uvicorn no boot ────────────────────────────────
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>HMPCF Backend FastAPI - Sistema hospitalar 24/7</Description>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
      <Delay>PT15S</Delay>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>999</Count>
    </RestartOnFailure>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$uvicorn</Command>
      <Arguments>$args</Arguments>
      <WorkingDirectory>$workDir</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

Register-ScheduledTask -Xml $xml -TaskName $taskName -Force | Out-Null
Write-Host "[OK] Tarefa '$taskName' registrada (reinicio automatico 999x)." -ForegroundColor Green

# ── 2. Watchdog: reinicia uvicorn se travar/morrer (verifica a cada 2 min) ────
$watchdogName = "HMPCF-Watchdog"
Unregister-ScheduledTask -TaskName $watchdogName -Confirm:$false -ErrorAction SilentlyContinue

# Cria o script watchdog
$watchdogContent = @'
$logFile = "C:\HMPCF-Automation-System\logs\watchdog.log"
$uvicorn  = "C:\HMPCF-Automation-System\backend\.venv\Scripts\uvicorn.exe"
$args     = "app.main:app --host 0.0.0.0 --port 8001"
$workDir  = "C:\HMPCF-Automation-System\backend"

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts $msg" | Out-File $logFile -Append -Encoding utf8
}

$proc = Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Log "[WATCHDOG] uvicorn nao encontrado — reiniciando..."
    Start-Process -FilePath $uvicorn -ArgumentList $args -WorkingDirectory $workDir -WindowStyle Hidden
    Start-Sleep 5
    $proc2 = Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue
    if ($proc2) {
        Write-Log "[WATCHDOG] Backend reiniciado com sucesso (PID $($proc2.Id))."
    } else {
        Write-Log "[WATCHDOG] FALHA ao reiniciar o backend."
    }
} else {
    # Testa health endpoint
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($r.StatusCode -ne 200) { throw "HTTP $($r.StatusCode)" }
    } catch {
        Write-Log "[WATCHDOG] Health check falhou ($_) — matando e reiniciando..."
        $proc | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep 2
        Start-Process -FilePath $uvicorn -ArgumentList $args -WorkingDirectory $workDir -WindowStyle Hidden
        Start-Sleep 5
        Write-Log "[WATCHDOG] Backend reiniciado apos health check falhar."
    }
}
'@
$watchdogContent | Out-File -FilePath $watcher -Encoding utf8 -Force

$xmlW = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>HMPCF Watchdog — monitora e reinicia backend se cair</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT2M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>2026-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
    <BootTrigger>
      <Enabled>true</Enabled>
      <Delay>PT30S</Delay>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-NonInteractive -ExecutionPolicy Bypass -File "$watcher"</Arguments>
    </Exec>
  </Actions>
</Task>
"@

Register-ScheduledTask -Xml $xmlW -TaskName $watchdogName -Force | Out-Null
Write-Host "[OK] Watchdog '$watchdogName' registrado (verifica a cada 2 min)." -ForegroundColor Green

# ── 3. Firewall porta 8001 ────────────────────────────────────────────────────
$fw = Get-NetFirewallRule -DisplayName "HMPCF Backend" -ErrorAction SilentlyContinue
if (-not $fw) {
    New-NetFirewallRule -DisplayName "HMPCF Backend" -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow -Profile Domain,Private,Public | Out-Null
    Write-Host "[OK] Firewall liberado na porta 8001." -ForegroundColor Green
} else {
    Write-Host "[OK] Firewall ja configurado." -ForegroundColor Green
}

# ── 4. Inicia agora se não estiver rodando ────────────────────────────────────
$proc = Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue
if (-not $proc) {
    Start-ScheduledTask -TaskName $taskName
    Start-Sleep 5
    $proc = Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue
}

if ($proc) {
    Write-Host "[OK] Backend rodando (PID $($proc.Id))." -ForegroundColor Green
} else {
    Write-Host "[AVISO] Backend nao iniciou automaticamente." -ForegroundColor Yellow
    Write-Host "        Execute manualmente: Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " HMPCF configurado para rodar 24/7:" -ForegroundColor Cyan
Write-Host "  - Inicia automaticamente no boot" -ForegroundColor Cyan
Write-Host "  - Watchdog verifica a cada 2 minutos" -ForegroundColor Cyan
Write-Host "  - Reinicia ate 999x em caso de falha" -ForegroundColor Cyan
Write-Host "  - Logs em: $logDir\" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Teste: Invoke-WebRequest http://localhost:8001/health | Select-Object -Expand Content" -ForegroundColor Cyan
