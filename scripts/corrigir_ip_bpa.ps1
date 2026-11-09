# Correcao de uso unico: servidor voltou para 192.168.1.29 (estava 192.168.1.229).
#
# Rode no notebook do BPA (PowerShell normal, nao precisa de administrador):
#   powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/fabiogomes95/HMPCF-Automation-System/main/scripts/corrigir_ip_bpa.ps1 | iex"
#
# O que faz:
#   1. Atualiza o sistema (git pull) se a pasta for um clone do git
#   2. Troca 192.168.1.229 -> 192.168.1.29 no atalho (abrir_bpa.vbs), no
#      instalador, no config do BPA e no bpa\.env (POSTGRES_HOST e origens)
#   3. Fecha o BPA que estiver rodando/travado e liga de novo pela tarefa
#   4. Testa: servidor (8001/5432) e BPA aceitando o sistema do novo IP
# Pode rodar mais de uma vez sem problema.

function Invoke-CorrigirIpBpa {
    $IP_NOVO   = "192.168.1.29"
    $IP_VELHO  = "192.168.1.229"
    $NOME_SERV = "desktop-9c4s1co"
    $raiz      = "C:\HMPCF-Automation-System"
    $bpa       = Join-Path $raiz "bpa"
    $tarefa    = "HMPCF-BPA"
    $origemNova = "http://${IP_NOVO}:8001"

    function Ok($m)    { Write-Host "[OK] $m" -ForegroundColor Green }
    function Aviso($m) { Write-Host "[AVISO] $m" -ForegroundColor Yellow }
    function Erro($m)  { Write-Host "[ERRO] $m" -ForegroundColor Red }

    # Le/grava texto mantendo o BOM do arquivo (se tiver) e sem mexer no resto
    function Trocar-NoArquivo($caminho, $de, $para) {
        if (-not (Test-Path $caminho)) { return $false }
        $bytes = [IO.File]::ReadAllBytes($caminho)
        $temBom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
        $texto = [IO.File]::ReadAllText($caminho, [Text.Encoding]::UTF8)
        if (-not $texto.Contains($de)) { return $false }
        [IO.File]::WriteAllText($caminho, $texto.Replace($de, $para), (New-Object Text.UTF8Encoding($temBom)))
        return $true
    }

    Write-Host ""
    Write-Host "=== Corrigir IP do servidor no BPA ($IP_VELHO -> $IP_NOVO) ===" -ForegroundColor Cyan

    if (-not (Test-Path (Join-Path $bpa "executar.py"))) {
        Erro "Nao achei o BPA em $bpa"
        return
    }

    # 1. Atualizar pelo git ------------------------------------------------------
    if ((Test-Path (Join-Path $raiz ".git")) -and (Get-Command git -ErrorAction SilentlyContinue)) {
        $saida = & git -C $raiz pull --ff-only origin main 2>&1
        if ($LASTEXITCODE -eq 0) { Ok "Sistema atualizado (git pull)" }
        else { Aviso "git pull nao rodou (corrijo os arquivos direto): $($saida | Select-Object -Last 1)" }
    } else {
        Aviso "Sem git nesta pasta -- corrijo os arquivos direto"
    }

    # 2. Arquivos do BPA ---------------------------------------------------------
    foreach ($rel in "abrir_bpa.vbs", "instalar.ps1", "bpa_local\config.py") {
        if (Trocar-NoArquivo (Join-Path $bpa $rel) $IP_VELHO $IP_NOVO) { Ok "IP trocado em bpa\$rel" }
    }
    Ok "Atalho/instalador/config apontando para $IP_NOVO"

    # bpa\.env: POSTGRES_HOST e lista de origens (com copia de seguranca)
    $envf = Join-Path $bpa ".env"
    if (Test-Path $envf) {
        $bytes = [IO.File]::ReadAllBytes($envf)
        $temBom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
        $linhas = [IO.File]::ReadAllLines($envf, [Text.Encoding]::UTF8)
        $mudou = $false
        $novas = foreach ($l in $linhas) {
            if ($l -match '^\s*BPA_ORIGENS_PERMITIDAS\s*=\s*(.*)$') {
                $lista = @($Matches[1].Split(",") | ForEach-Object { $_.Trim().TrimEnd("/").Replace($IP_VELHO, $IP_NOVO) } | Where-Object { $_ })
                $lista = @($origemNova, "http://${NOME_SERV}:8001") + $lista | Select-Object -Unique
                $nova = "BPA_ORIGENS_PERMITIDAS=" + ($lista -join ",")
                if ($nova -ne $l) { $mudou = $true }
                $nova
            } elseif ($l -notmatch '^\s*#' -and $l.Contains($IP_VELHO)) {
                $mudou = $true
                $l.Replace($IP_VELHO, $IP_NOVO)
            } else { $l }
        }
        if ($mudou) {
            Copy-Item $envf "$envf.bak-$(Get-Date -Format yyyyMMdd-HHmmss)"
            [IO.File]::WriteAllLines($envf, [string[]]$novas, (New-Object Text.UTF8Encoding($temBom)))
            Ok "bpa\.env corrigido (copia antiga salva como .env.bak-...)"
        } else {
            Ok "bpa\.env ja estava certo"
        }
    } else {
        Aviso "bpa\.env nao existe -- rode o bpa\instalar.ps1 depois"
    }

    # Descricao do atalho da area de trabalho
    $lnkPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "HMPCF - BPA.lnk"
    if (Test-Path $lnkPath) {
        $sh = New-Object -ComObject WScript.Shell
        $lnk = $sh.CreateShortcut($lnkPath)
        $lnk.Description = "Sistema HMPCF (aba BPA) - $origemNova"
        $lnk.Save()
        Ok "Atalho 'HMPCF - BPA' abre $origemNova"
    }

    # 3. Servidor responde? -------------------------------------------------------
    foreach ($p in 8001, 5432) {
        $t = Test-NetConnection $IP_NOVO -Port $p -WarningAction SilentlyContinue
        if ($t.TcpTestSucceeded) { Ok "Servidor ${IP_NOVO}:$p respondendo" }
        else { Erro "Servidor ${IP_NOVO}:$p NAO responde (servidor ligado? mesma rede?)" }
    }

    # 4. Reiniciar o BPA (inclusive copia travada que nao abriu a porta) ---------
    Stop-ScheduledTask -TaskName $tarefa -ErrorAction SilentlyContinue
    Get-CimInstance Win32_Process -Filter "Name='pythonw.exe' OR Name='python.exe'" |
        Where-Object { $_.CommandLine -match "executar\.py|bpa\\app\.py" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
    try { Start-ScheduledTask -TaskName $tarefa -ErrorAction Stop; Ok "BPA ligado pela tarefa $tarefa" }
    catch {
        Start-Process -FilePath (Join-Path $bpa ".venv\Scripts\pythonw.exe") -ArgumentList "executar.py" -WorkingDirectory $bpa
        Ok "BPA ligado direto (sem a tarefa)"
    }

    Write-Host "     Esperando o BPA carregar os pacientes (ate 3 min)..."
    $no_ar = $false
    for ($i = 0; $i -lt 60 -and -not $no_ar; $i++) {
        Start-Sleep -Seconds 3
        $no_ar = [bool](Get-NetTCPConnection -LocalPort 8503 -State Listen -ErrorAction SilentlyContinue)
    }
    if (-not $no_ar) {
        Erro "BPA nao abriu a porta 8503. Veja o fim de $bpa\bpa_local.log"
        return
    }

    try {
        $r = Invoke-WebRequest -UseBasicParsing -Method Options -Uri "http://127.0.0.1:8503/api/status" -Headers @{
            Origin = $origemNova; "Access-Control-Request-Method" = "GET"; "Access-Control-Request-Private-Network" = "true" }
        if ($r.Headers["Access-Control-Allow-Origin"] -eq $origemNova) { Ok "BPA aceita o sistema em $origemNova" }
        else { Erro "BPA respondeu mas sem liberar $origemNova" }
    } catch {
        Erro "BPA recusou $origemNova ($($_.Exception.Message))"
        return
    }

    Write-Host ""
    Write-Host "Pronto. Abra o atalho 'HMPCF - BPA' (ou $origemNova e aperte Ctrl+F5)." -ForegroundColor Cyan
}

Invoke-CorrigirIpBpa
