# Atualiza o servidor para a versao mais nova do GitHub (main) e, se algo der
# errado depois de baixar, VOLTA SOZINHO para a versao que estava rodando.
#
#   1. confere que o codigo deste servidor nao tem alteracao feita a mao
#   2. anota a versao atual (ponto de retorno)
#   3. baixa a versao nova, instala dependencias e monta as telas
#   4. reinicia o HMPCF-Backend-Svc (5 a 10 s fora do ar; ninguem perde o login)
#   5. espera o /health responder ok por ate 30 s
#   6. qualquer falha em 3-5: volta para o ponto de retorno, remonta, reinicia
#
# Nao mexe no banco: se a versao nova trouxer migracao (backend/migrations),
# para ANTES de baixar e pede para fazer a mao (docs/RECUPERACAO_SERVIDOR.md).
#
# Uso (PowerShell como administrador):
#   powershell -ExecutionPolicy Bypass -File C:\HMPCF-Automation-System\scripts\servidor\atualizar.ps1
# Opcoes:
#   -Forcar               reinstala e reinicia mesmo sem versao nova
#   -SimularFalhaHealth   so para testar a volta automatica (finge que o health falhou uma vez)
#
# Saida: 0 = atualizado (ou nada a fazer) | 1 = parou antes de mexer em nada
#        2 = deu errado e VOLTOU para a versao anterior (sistema no ar)
#        3 = deu errado e NAO conseguiu voltar (ver backend\nssm_backend.log)
# Registro de cada execucao: C:\HMPCF\atualizacoes.log

param([switch]$Forcar, [switch]$SimularFalhaHealth)

$Servico = "HMPCF-Backend-Svc"
$Raiz    = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Log     = "C:\HMPCF\atualizacoes.log"
$Health  = "http://127.0.0.1:8001/health"
$script:simularFalha = $SimularFalhaHealth.IsPresent

# Sem $ErrorActionPreference = "Stop" de proposito: no PowerShell 5.1 ele
# transforma o aviso que o pip/npm escrevem no stderr em erro. Quem decide se
# um comando falhou e o codigo de saida ($LASTEXITCODE).

function Escrever($msg, $cor = "Gray") {
    Write-Host $msg -ForegroundColor $cor
    Add-Content -Path $Log -Value ("{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $msg) -Encoding UTF8
}

function GitCmd {
    $saida = & git -C $Raiz @args 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) { throw "git $($args -join ' ') falhou: $($saida -join ' | ')" }
    $saida
}

# Comando demorado (pip/npm): a saida vai so para o log; falha = codigo != 0
function Rodar($descricao, [scriptblock]$comando) {
    Escrever "  $descricao..."
    $saida = & $comando 2>&1 | ForEach-Object { "$_" }
    $codigo = $LASTEXITCODE
    $saida | Add-Content -Path $Log -Encoding UTF8
    if ($codigo -ne 0) { throw "$descricao falhou (codigo $codigo) -- detalhes em $Log" }
}

function Reiniciar-Servico {
    Escrever "  Reiniciando o sistema (5 a 10 s fora do ar)..."
    & sc.exe stop $Servico | Out-Null
    $limite = (Get-Date).AddSeconds(15)
    while ((Get-Service $Servico).Status -ne "Stopped" -and (Get-Date) -lt $limite) { Start-Sleep -Milliseconds 500 }
    if ((Get-Service $Servico).Status -ne "Stopped") {
        # Ja aconteceu de travar em StopPending: o Python sai e o nssm fica preso
        $processo = (Get-CimInstance Win32_Service -Filter "Name='$Servico'").ProcessId
        Escrever "  O servico travou ao parar -- encerrando o processo $processo" "Yellow"
        if ($processo) { Stop-Process -Id $processo -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 2
    }
    Start-Service $Servico
}

function Sistema-Respondeu {
    if ($script:simularFalha) {
        $script:simularFalha = $false
        Escrever "  [TESTE] fingindo que o sistema nao respondeu" "Yellow"
        return $false
    }
    $limite = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $limite) {
        try { if ((Invoke-RestMethod $Health -TimeoutSec 3).status -eq "ok") { return $true } } catch {}
        Start-Sleep -Seconds 1
    }
    return $false
}

New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null
Escrever ""
Escrever "===== Atualizacao do HMPCF =====" "Cyan"

# -- 1. Conferencias (nada foi mexido ainda) ----------------------------------
try {
    $alterados = GitCmd status --porcelain
    if ($alterados) {
        Escrever "[PARADO] Este servidor tem arquivos alterados a mao. Nada foi feito." "Red"
        $alterados | ForEach-Object { Escrever "    $_" "Red" }
        Escrever "Mostre esta lista para quem cuida do sistema antes de atualizar." "Red"
        exit 1
    }
    GitCmd fetch origin | Out-Null
    if ([int](GitCmd rev-list --count origin/main..HEAD) -gt 0) {
        Escrever "[PARADO] Este servidor tem versoes que nao estao no GitHub. Nada foi feito." "Red"
        GitCmd log --oneline origin/main..HEAD | ForEach-Object { Escrever "    $_" "Red" }
        exit 1
    }
    $antes = GitCmd rev-parse --short HEAD
    $novos = [int](GitCmd rev-list --count HEAD..origin/main)
    if ($novos -eq 0 -and -not $Forcar) {
        Escrever "[OK] Ja esta na versao mais nova ($antes). Nada a fazer." "Green"
        exit 0
    }
    $migracoes = GitCmd diff --name-only HEAD origin/main -- backend/migrations/versions
    if ($migracoes) {
        Escrever "[PARADO] A versao nova muda o banco de dados. Nada foi feito." "Red"
        $migracoes | ForEach-Object { Escrever "    $_" "Red" }
        Escrever "Faca essa atualizacao a mao (alembic upgrade head), com backup antes." "Red"
        exit 1
    }
} catch {
    Escrever "[PARADO] $($_.Exception.Message)" "Red"
    exit 1
}

Escrever "Versao atual: $antes  (ponto de retorno)"
if ($novos -gt 0) {
    Escrever "Versoes novas: $novos"
    GitCmd log --oneline HEAD..origin/main | ForEach-Object { Escrever "    $_" }
} else {
    Escrever "Sem versao nova -- reinstalando e reiniciando (-Forcar)"
}

# -- 2. Atualizar; qualquer falha daqui pra frente volta para $antes ----------
try {
    if ($novos -gt 0) { Rodar "Baixando a versao nova" { git -C $Raiz pull --ff-only origin main } }
    Rodar "Instalando dependencias do sistema" { & "$Raiz\backend\.venv\Scripts\python.exe" -m pip install -r "$Raiz\backend\requirements.txt" }
    Rodar "Instalando dependencias das telas" { npm.cmd --prefix "$Raiz\frontend" install }
    Rodar "Montando as telas" { npm.cmd --prefix "$Raiz\frontend" run build }
    Reiniciar-Servico
    if (-not (Sistema-Respondeu)) { throw "o sistema nao respondeu em 30 s depois de reiniciar" }
} catch {
    Escrever "[ERRO] $($_.Exception.Message)" "Red"
    Escrever "Voltando para a versao $antes..." "Yellow"
    try {
        # O codigo estava limpo (conferido no passo 1): o reset so desfaz o que
        # o pull trouxe. As versoes novas continuam no GitHub para tentar depois.
        if ($novos -gt 0) { GitCmd reset --hard $antes | Out-Null }
        Rodar "Montando as telas da versao $antes" { npm.cmd --prefix "$Raiz\frontend" run build }
        Reiniciar-Servico
        if (Sistema-Respondeu) {
            Escrever "[VOLTOU] O sistema voltou para a versao $antes e esta funcionando." "Yellow"
            Escrever "A atualizacao NAO foi aplicada. Detalhes em $Log" "Yellow"
            exit 2
        }
        throw "o sistema nao respondeu nem na versao anterior"
    } catch {
        Escrever "[URGENTE] $($_.Exception.Message)" "Red"
        Escrever "Veja o fim de $Raiz\backend\nssm_backend.log e docs\RECUPERACAO_SERVIDOR.md" "Red"
        exit 3
    }
}

Escrever "[OK] Atualizado: $antes -> $(GitCmd rev-parse --short HEAD). Sistema no ar." "Green"
exit 0
