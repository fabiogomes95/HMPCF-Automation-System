# Descriptografa um backup gerado por encrypt_backup.ps1.
# Le a senha de scripts/windows/.backup_passphrase se existir (mesma maquina
# que gerou o backup); senao pede interativamente (nao aparece na tela).
#
# Uso: powershell -File decrypt_backup.ps1 -Path "C:\HMPCF\backups\hmpcf_2026-07-02.sql.enc"
# Gera: C:\HMPCF\backups\hmpcf_2026-07-02.sql (ao lado do .enc)

param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Path)) {
    Write-Error "Arquivo nao encontrado: $Path"
    exit 1
}

$passphraseFile = Join-Path $PSScriptRoot ".backup_passphrase"
if (Test-Path $passphraseFile) {
    $passphrase = (Get-Content $passphraseFile -Raw).Trim()
} else {
    $securePass = Read-Host -Prompt "Senha de criptografia do backup" -AsSecureString
    $passphrase = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePass)
    )
}

$allBytes = [System.IO.File]::ReadAllBytes($Path)
$salt = $allBytes[0..15]
$iv   = $allBytes[16..31]
$cipherBytes = $allBytes[32..($allBytes.Length - 1)]

$deriveBytes = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($passphrase, $salt, 100000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
$key = $deriveBytes.GetBytes(32)

$aes = [System.Security.Cryptography.Aes]::Create()
$aes.Key  = $key
$aes.IV   = $iv
$aes.Mode = [System.Security.Cryptography.CipherMode]::CBC

try {
    $decryptor  = $aes.CreateDecryptor()
    $plainBytes = $decryptor.TransformFinalBlock($cipherBytes, 0, $cipherBytes.Length)
} catch {
    Write-Error "Falha ao descriptografar — senha incorreta ou arquivo corrompido."
    exit 1
}

$outPath = $Path -replace '\.enc$', ''
[System.IO.File]::WriteAllBytes($outPath, $plainBytes)

Write-Host "[OK] Backup restaurado: $outPath"
