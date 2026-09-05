# Copia o backup criptografado do dia para uma pasta local sincronizada
# (OneDrive por padrão) e aplica a mesma retenção lá também — protege
# contra falha de disco/incêndio/roubo na máquina de produção, já que
# scripts/windows/backup_postgres.bat só guarda em C:\HMPCF\backups\
# (mesma máquina do Postgres).
#
# NUNCA copiar scripts/windows/.backup_passphrase para esta pasta —
# guardar a senha de criptografia ao lado do dado criptografado anula a
# proteção (ver docs/DEPLOY_HOSPITAL.md, seção 9.6).
#
# Uso:
#   powershell -File copiar_backup_onedrive.ps1 -Path "C:\HMPCF\backups\hmpcf_2026-07-02.sql.enc"
#   powershell -File copiar_backup_onedrive.ps1 -Path "..." -DestinoPasta "D:\outro\lugar"
#
# Falha aqui NUNCA deve derrubar o backup inteiro — quem chama (
# backup_postgres.bat) só avisa e segue; o backup local já está feito e
# íntegro antes deste passo rodar.

param(
    [Parameter(Mandatory = $true)]
    [string]$Path,

    [string]$DestinoPasta = (Join-Path $env:USERPROFILE "OneDrive\HMPCF-Backups"),

    [int]$RetencaoDias = 30
)

# Sem isso, erros de cmdlet (drive inexistente, sem permissao, etc.) sao
# "nao terminantes" por padrao no PowerShell -- nao disparam o catch abaixo
# e o script seguiria em frente reportando [OK] mesmo tendo falhado.
$ErrorActionPreference = "Stop"

if (-not (Test-Path $Path)) {
    Write-Warning "Arquivo de origem nao encontrado: $Path -- pulando copia externa."
    exit 1
}

try {
    if (-not (Test-Path $DestinoPasta)) {
        New-Item -ItemType Directory -Path $DestinoPasta -Force | Out-Null
    }

    $destino = Join-Path $DestinoPasta (Split-Path $Path -Leaf)
    Copy-Item -Path $Path -Destination $destino -Force

    Get-ChildItem $DestinoPasta -Filter *.sql.enc |
        Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$RetencaoDias) } |
        Remove-Item -Force

    Write-Host "[OK] Copia externa: $destino"
}
catch {
    Write-Warning "Falha ao copiar backup para fora da maquina ($DestinoPasta): $($_.Exception.Message)"
    Write-Warning "O backup LOCAL ja foi feito com sucesso -- isso so afeta a copia externa de hoje."
    exit 1
}
