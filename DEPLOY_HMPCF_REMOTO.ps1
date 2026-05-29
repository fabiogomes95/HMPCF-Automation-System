#Requires -RunAsAdministrator

# =============================================================================
#  DEPLOY_HMPCF_REMOTO.ps1
#  Deploy completo do sistema HMPCF via terminal (sem acesso fisico)
#
#  COMO USAR (PowerShell como Administrador):
#    Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
#    .\DEPLOY_HMPCF_REMOTO.ps1
# =============================================================================

# =============================================================================
# CONFIGURACAO -- edite aqui antes de rodar
# =============================================================================

$PG_PASSWORD   = "hmpcf2026"
$PG_DB         = "hmpcf"
$PG_PORT       = 5432
$REPO_URL      = "https://github.com/fabiogomes95/HMPCF-Automation-System.git"
$INSTALL_ROOT  = "C:\HMPCF"
$BACKUP_DIR    = "$INSTALL_ROOT\backups"
$LOG_DIR       = "$INSTALL_ROOT\logs"
$NSSM_DIR      = "$INSTALL_ROOT\nssm"
$APP_PORT      = 8001
$PG_BIN        = "C:\Program Files\PostgreSQL\16\bin"

# =============================================================================
# FUNCOES AUXILIARES
# =============================================================================

function Log-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Log-Ok($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Log-Warn($msg) { Write-Host "    [AVISO] $msg" -ForegroundColor Yellow }
function Log-Error($msg){ Write-Host "    [ERRO] $msg" -ForegroundColor Red; exit 1 }

function Wait-ForService($name, $timeoutSec = 60) {
    $elapsed = 0
    while ($elapsed -lt $timeoutSec) {
        $svc = Get-Service $name -ErrorAction SilentlyContinue
        if ($svc -and $svc.Status -eq 'Running') { return $true }
        Start-Sleep 2
        $elapsed += 2
    }
    return $false
}

function Reload-PATH {
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" +
                $PG_BIN
}

# =============================================================================
# ETAPA 0 -- Verificar Windows
# =============================================================================

Log-Step "Verificando ambiente Windows..."

if (-not [System.Environment]::Is64BitOperatingSystem) {
    Log-Error "Sistema precisa ser 64-bit."
}
Log-Ok "Sistema 64-bit OK"
Log-Ok ("SO: " + (Get-WmiObject Win32_OperatingSystem).Caption)

# =============================================================================
# ETAPA 1 -- Verificar winget
# =============================================================================

Log-Step "Verificando winget..."
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Log-Error "winget nao encontrado. Atualize o Windows ou instale o App Installer pela Microsoft Store."
}
Log-Ok "winget disponivel"

# =============================================================================
# ETAPA 2 -- Instalar PostgreSQL 16
# =============================================================================

Log-Step "Instalando PostgreSQL 16..."

$pgService = Get-Service "postgresql-x64-16" -ErrorAction SilentlyContinue
if ($pgService) {
    Log-Warn "PostgreSQL ja instalado -- pulando"
} else {
    $pgInstaller = "$env:TEMP\postgresql-16-installer.exe"
    $pgUrl = "https://get.enterprisedb.com/postgresql/postgresql-16-3-1-windows-x64.exe"
    Write-Host "    Baixando instalador PostgreSQL 16 (~300 MB)..." -ForegroundColor Gray
    Invoke-WebRequest -Uri $pgUrl -OutFile $pgInstaller -UseBasicParsing

    $pgArgs = "--mode unattended --superpassword $PG_PASSWORD --serverport $PG_PORT --locale Portuguese_Brazil --unattendedmodeui none"
    Start-Process -FilePath $pgInstaller -ArgumentList $pgArgs -Wait -NoNewWindow
    Remove-Item $pgInstaller -Force

    if (-not (Wait-ForService "postgresql-x64-16" 90)) {
        Log-Error "Servico PostgreSQL nao iniciou apos instalacao."
    }
    Log-Ok "PostgreSQL 16 instalado e rodando"
}

# Adicionar bin ao PATH se necessario
$currentPath = [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
if ($currentPath -notlike ("*" + $PG_BIN + "*")) {
    [System.Environment]::SetEnvironmentVariable("PATH", ($currentPath + ";" + $PG_BIN), "Machine")
    Log-Ok "PostgreSQL bin adicionado ao PATH"
} else {
    Log-Ok "PostgreSQL bin ja esta no PATH"
}
Reload-PATH

# =============================================================================
# ETAPA 3 -- Instalar Python, Git, Node.js via winget
# =============================================================================

Log-Step "Instalando Python 3.11..."
if ((Get-Command python -ErrorAction SilentlyContinue) -and ((python --version 2>&1) -match "3\.1[1-9]")) {
    Log-Warn "Python ja instalado -- pulando"
} else {
    winget install --id Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements
    Reload-PATH
    Log-Ok "Python 3.11 instalado"
}

Log-Step "Instalando Git..."
if (Get-Command git -ErrorAction SilentlyContinue) {
    Log-Warn "Git ja instalado -- pulando"
} else {
    winget install --id Git.Git --silent --accept-source-agreements --accept-package-agreements
    Reload-PATH
    Log-Ok "Git instalado"
}

Log-Step "Instalando Node.js LTS..."
if (Get-Command node -ErrorAction SilentlyContinue) {
    Log-Warn "Node.js ja instalado -- pulando"
} else {
    winget install --id OpenJS.NodeJS.LTS --silent --accept-source-agreements --accept-package-agreements
    Reload-PATH
    Log-Ok "Node.js instalado"
}

# =============================================================================
# ETAPA 4 -- Verificar comandos
# =============================================================================

Log-Step "Verificando comandos instalados..."
Reload-PATH

foreach ($cmd in @("python", "git", "node", "npm", "psql", "pg_dump")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        Log-Ok ("$cmd OK: " + (& $cmd --version 2>&1 | Select-Object -First 1))
    } else {
        Log-Warn "$cmd nao encontrado no PATH -- pode ser necessario reiniciar o PowerShell"
    }
}

# =============================================================================
# ETAPA 5 -- Criar pastas
# =============================================================================

Log-Step "Criando estrutura de pastas..."
foreach ($dir in @($INSTALL_ROOT, $BACKUP_DIR, $LOG_DIR, $NSSM_DIR)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Log-Ok ("Pasta: " + $dir)
}

# =============================================================================
# ETAPA 6 -- Clonar ou atualizar repositorio
# =============================================================================

Log-Step "Clonando / atualizando repositorio..."
if (Test-Path ($INSTALL_ROOT + "\.git")) {
    Log-Warn "Repositorio ja existe -- fazendo git pull"
    Set-Location $INSTALL_ROOT
    git pull origin main
} else {
    git clone $REPO_URL $INSTALL_ROOT
}

foreach ($f in @(
    ($INSTALL_ROOT + "\backend\app\main.py"),
    ($INSTALL_ROOT + "\frontend\src\App.jsx"),
    ($INSTALL_ROOT + "\scripts\migrate_to_postgres.py"),
    ($INSTALL_ROOT + "\legado\hospital.db")
)) {
    if (Test-Path $f) { Log-Ok ("Encontrado: " + $f) }
    else { Log-Error ("Arquivo nao encontrado: " + $f) }
}

# =============================================================================
# ETAPA 7 -- Configurar PostgreSQL e criar banco
# =============================================================================

Log-Step "Configurando PostgreSQL..."

if (-not (Wait-ForService "postgresql-x64-16" 30)) {
    Log-Error "Servico PostgreSQL nao esta rodando."
}

$env:PGPASSWORD = $PG_PASSWORD

$dbExists = & "$PG_BIN\psql.exe" -U postgres -h localhost -tAc ("SELECT 1 FROM pg_database WHERE datname='" + $PG_DB + "';")
if ($dbExists -eq "1") {
    Log-Warn ("Banco '" + $PG_DB + "' ja existe -- pulando criacao")
} else {
    $sql = "CREATE DATABASE " + $PG_DB + " WITH ENCODING 'UTF8' LC_COLLATE 'Portuguese_Brazil.1252' LC_CTYPE 'Portuguese_Brazil.1252' TEMPLATE template0;"
    & "$PG_BIN\psql.exe" -U postgres -h localhost -c $sql
    Log-Ok ("Banco '" + $PG_DB + "' criado")
}

$pgVersion = & "$PG_BIN\psql.exe" -U postgres -h localhost -d $PG_DB -tAc "SELECT version();"
if (-not $pgVersion) { Log-Error "Nao foi possivel conectar ao banco." }
Log-Ok "Conexao com o banco OK"

# =============================================================================
# ETAPA 8 -- Criar .env do backend
# =============================================================================

Log-Step "Criando .env do backend..."

$backendEnvPath = $INSTALL_ROOT + "\backend\.env"
$backendEnvContent = @(
    "APP_NAME=HMPCF",
    "ENVIRONMENT=production",
    "",
    ("POSTGRES_HOST=localhost"),
    ("POSTGRES_PORT=" + $PG_PORT),
    ("POSTGRES_USER=postgres"),
    ("POSTGRES_PASSWORD=" + $PG_PASSWORD),
    ("POSTGRES_DB=" + $PG_DB),
    "",
    "DATABASE_POOL_SIZE=10",
    "DATABASE_MAX_OVERFLOW=20",
    "DATABASE_POOL_PRE_PING=true",
    "",
    'CORS_ORIGINS=["*"]'
)
$backendEnvContent | Set-Content -Path $backendEnvPath -Encoding UTF8
Log-Ok ".env do backend criado"

# =============================================================================
# ETAPA 9 -- Venv e dependencias do backend
# =============================================================================

Log-Step "Criando venv do backend e instalando dependencias..."

Set-Location ($INSTALL_ROOT + "\backend")
python -m venv .venv
& ".venv\Scripts\pip.exe" install --upgrade pip --quiet
& ".venv\Scripts\pip.exe" install -r requirements.txt --quiet

$check = & ".venv\Scripts\python.exe" -c "import fastapi, uvicorn, sqlalchemy, asyncpg; print('OK')" 2>&1
if ($check -ne "OK") { Log-Error ("Erro nas dependencias do backend: " + $check) }
Log-Ok "Dependencias do backend OK"

# =============================================================================
# ETAPA 10 -- Migracao SQLite -> PostgreSQL
# =============================================================================

Log-Step "Preparando migracao SQLite -> PostgreSQL..."

Set-Location ($INSTALL_ROOT + "\scripts")
python -m venv .venv
& ".venv\Scripts\pip.exe" install --upgrade pip --quiet
& ".venv\Scripts\pip.exe" install psycopg2-binary python-dotenv --quiet

$migEnvContent = @(
    "SQLITE_PATH=../legado/hospital.db",
    ("POSTGRES_HOST=localhost"),
    ("POSTGRES_PORT=" + $PG_PORT),
    ("POSTGRES_DB=" + $PG_DB),
    ("POSTGRES_USER=postgres"),
    ("POSTGRES_PASSWORD=" + $PG_PASSWORD),
    "LOG_FILE=migration.log",
    "BATCH_SIZE=500"
)
$migEnvContent | Set-Content -Path ($INSTALL_ROOT + "\scripts\.env") -Encoding UTF8
Log-Ok ".env de migracao criado"

# migrate_to_postgres.py ja cria as tabelas (Etapa 0) e migra pacientes + atendimentos
Log-Step "Criando tabelas e migrando dados (SQLite -> PostgreSQL)..."
& ".venv\Scripts\python.exe" migrate_to_postgres.py
if ($LASTEXITCODE -ne 0) { Log-Error "Migracao falhou. Veja scripts\migration.log" }
Log-Ok "Migracao concluida"

Log-Step "Validando migracao..."
$pacCount = & "$PG_BIN\psql.exe" -U postgres -h localhost -d $PG_DB -tAc "SELECT COUNT(*) FROM pacientes;"
$atdCount = & "$PG_BIN\psql.exe" -U postgres -h localhost -d $PG_DB -tAc "SELECT COUNT(*) FROM recepcao_atendimentos;"
Log-Ok ("Pacientes migrados   : " + $pacCount.Trim())
Log-Ok ("Atendimentos migrados: " + $atdCount.Trim())

# =============================================================================
# ETAPA 11 -- Build do frontend
# =============================================================================

Log-Step "Build do frontend..."

Set-Location ($INSTALL_ROOT + "\frontend")
npm install --silent
npm run build

if (-not (Test-Path ($INSTALL_ROOT + "\frontend\dist\index.html"))) {
    Log-Error "Build do frontend falhou."
}
Log-Ok "Frontend buildado"

# =============================================================================
# ETAPA 12 -- NSSM
# =============================================================================

Log-Step "Baixando NSSM..."

$nssmExe = $NSSM_DIR + "\nssm.exe"
if (-not (Test-Path $nssmExe)) {
    $nssmZip     = "$env:TEMP\nssm.zip"
    $nssmExtract = "$env:TEMP\nssm_extract"
    Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile $nssmZip -UseBasicParsing
    Expand-Archive -Path $nssmZip -DestinationPath $nssmExtract -Force
    $nssmBin = Get-ChildItem -Path $nssmExtract -Recurse -Filter "nssm.exe" | Where-Object { $_.FullName -like "*win64*" } | Select-Object -First 1
    Copy-Item $nssmBin.FullName -Destination $nssmExe -Force
    Remove-Item $nssmZip, $nssmExtract -Recurse -Force
    Log-Ok "NSSM instalado"
} else {
    Log-Warn "NSSM ja existe -- pulando"
}

# =============================================================================
# ETAPA 13 -- Registrar servico Windows
# =============================================================================

Log-Step "Registrando servico HMPCF-Backend..."

$svcName     = "HMPCF-Backend"
$uvicornExe  = $INSTALL_ROOT + "\backend\.venv\Scripts\uvicorn.exe"
$uvicornArgs = "app.main:app --host 0.0.0.0 --port " + $APP_PORT

$existing = Get-Service $svcName -ErrorAction SilentlyContinue
if ($existing) {
    Log-Warn "Servico ja existe -- removendo para reinstalar"
    & $nssmExe stop $svcName confirm 2>$null
    & $nssmExe remove $svcName confirm 2>$null
    Start-Sleep 3
}

& $nssmExe install $svcName $uvicornExe $uvicornArgs
& $nssmExe set $svcName AppDirectory ($INSTALL_ROOT + "\backend")
& $nssmExe set $svcName DisplayName "HMPCF Backend (FastAPI)"
& $nssmExe set $svcName Start SERVICE_AUTO_START
& $nssmExe set $svcName AppStdout ($LOG_DIR + "\backend.log")
& $nssmExe set $svcName AppStderr ($LOG_DIR + "\backend_err.log")
& $nssmExe set $svcName AppRotateFiles 1
& $nssmExe set $svcName AppRotateSeconds 86400
& $nssmExe set $svcName AppThrottle 5000
& $nssmExe start $svcName

if (-not (Wait-ForService $svcName 30)) {
    Log-Error ("Servico nao iniciou. Veja: " + $LOG_DIR + "\backend_err.log")
}
Log-Ok "Servico HMPCF-Backend rodando"

# =============================================================================
# ETAPA 14 -- Backup automatico
# =============================================================================

Log-Step "Configurando backup automatico..."

[System.Environment]::SetEnvironmentVariable("PGPASSWORD", $PG_PASSWORD, "Machine")

$backupBat = @(
    "@echo off",
    ("set PGPASSWORD=" + $PG_PASSWORD),
    ("set BACKUP_DIR=" + $BACKUP_DIR),
    ("set DB=" + $PG_DB),
    ('if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"'),
    ('for /f "tokens=*" %%a in (''powershell -NoProfile -Command "Get-Date -Format ''yyyy-MM-dd''"'') do set DATESTAMP=%%a'),
    ('set OUTFILE=%BACKUP_DIR%\hmpcf_%DATESTAMP%.sql'),
    "echo Iniciando backup...",
    ('"' + $PG_BIN + '\pg_dump.exe" -U postgres -h localhost -d %DB% -f "%OUTFILE%"'),
    'if %ERRORLEVEL% EQU 0 (echo [OK] Backup: %OUTFILE%) else (echo [ERRO] Falha no backup! & exit /b 1)',
    ("powershell -NoProfile -Command ""Get-ChildItem '" + $BACKUP_DIR + "' -Filter *.sql | Where-Object { `$_.LastWriteTime -lt (Get-Date).AddDays(-30) } | Remove-Item -Force""")
)
$backupBat | Set-Content -Path ($INSTALL_ROOT + "\scripts\backup_postgres.bat") -Encoding ASCII
Log-Ok "Script de backup criado"

$taskName    = "HMPCF-Backup-Diario"
$taskAction  = New-ScheduledTaskAction -Execute ($INSTALL_ROOT + "\scripts\backup_postgres.bat")
$taskTrigger = New-ScheduledTaskTrigger -Daily -At "23:00"
$taskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger $taskTrigger -Settings $taskSettings -RunLevel Highest -Force | Out-Null
Log-Ok "Backup agendado para 23:00"

Log-Step "Executando backup inicial..."
& ($INSTALL_ROOT + "\scripts\backup_postgres.bat")
Log-Ok "Backup inicial OK"

# =============================================================================
# ETAPA 15 -- Firewall
# =============================================================================

Log-Step "Configurando firewall (porta $APP_PORT)..."

$fwRule = Get-NetFirewallRule -DisplayName "HMPCF Backend" -ErrorAction SilentlyContinue
if ($fwRule) {
    Log-Warn "Regra de firewall ja existe -- pulando"
} else {
    New-NetFirewallRule -DisplayName "HMPCF Backend" -Direction Inbound -Protocol TCP -LocalPort $APP_PORT -Action Allow -Profile Domain,Private | Out-Null
    Log-Ok ("Firewall liberado na porta " + $APP_PORT)
}

# =============================================================================
# ETAPA 16 -- Health check
# =============================================================================

Log-Step "Aguardando backend (15s)..."
Start-Sleep 15

Log-Step "Health check..."
try {
    $health = Invoke-WebRequest ("http://localhost:" + $APP_PORT + "/health") -UseBasicParsing -TimeoutSec 15
    Log-Ok ("Backend OK: " + $health.Content)
} catch {
    Log-Warn ("Nao foi possivel verificar /health agora. Teste manualmente: http://localhost:" + $APP_PORT + "/health")
}

$localIPObj = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.*" } | Select-Object -First 1
$localIP = if ($localIPObj) { $localIPObj.IPAddress } else { "SEM-IP-CONFIGURADO" }

# =============================================================================
# RESUMO
# =============================================================================

Write-Host ""
Write-Host "================================================================" -ForegroundColor White
Write-Host "  DEPLOY HMPCF CONCLUIDO" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor White
Write-Host ""
Write-Host "  Servicos:"
Write-Host ("    PostgreSQL ...... " + (Get-Service "postgresql-x64-16").Status)
Write-Host ("    HMPCF-Backend ... " + (Get-Service "HMPCF-Backend").Status)
Write-Host ""
Write-Host "  Acesso:"
Write-Host ("    Local:  http://localhost:" + $APP_PORT)
Write-Host ("    Rede:   http://" + $localIP + ":" + $APP_PORT)
Write-Host ("    Health: http://" + $localIP + ":" + $APP_PORT + "/health")
Write-Host ""
Write-Host ("  Backups: " + $BACKUP_DIR + " (diario 23:00)")
Write-Host ("  Logs:    " + $LOG_DIR + "\backend.log")
Write-Host ""
Write-Host "  Comandos uteis:"
Write-Host "    Ver status:   Get-Service postgresql-x64-16, HMPCF-Backend"
Write-Host ("    Ver logs:     Get-Content " + $LOG_DIR + "\backend.log -Tail 50 -Wait")
Write-Host "    Reiniciar:    net stop HMPCF-Backend; net start HMPCF-Backend"
Write-Host ""
Write-Host ("  >> IP da rede para as estacoes: http://" + $localIP + ":" + $APP_PORT)
Write-Host ""
