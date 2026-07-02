# Criptografa um arquivo (ex: dump do backup) com AES-256-CBC. Senha lida de
# um arquivo local nao versionado (scripts/windows/.backup_passphrase),
# mesmo padrao usado para backend/.env.
#
# Formato do .enc gerado: [salt 16 bytes][iv 16 bytes][ciphertext]
# Uso: powershell -File encrypt_backup.ps1 -Path "C:\HMPCF\backups\hmpcf_2026-07-02.sql"

param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = "Stop"

$passphraseFile = Join-Path $PSScriptRoot ".backup_passphrase"
if (-not (Test-Path $passphraseFile)) {
    Write-Error "Arquivo de senha nao encontrado: $passphraseFile"
    exit 1
}
$passphrase = (Get-Content $passphraseFile -Raw).Trim()
if ([string]::IsNullOrEmpty($passphrase)) {
    Write-Error "Arquivo de senha vazio: $passphraseFile"
    exit 1
}

if (-not (Test-Path $Path)) {
    Write-Error "Arquivo nao encontrado: $Path"
    exit 1
}

$salt = New-Object byte[] 16
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($salt)

$deriveBytes = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($passphrase, $salt, 100000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
$key = $deriveBytes.GetBytes(32)
$iv  = $deriveBytes.GetBytes(16)

$aes = [System.Security.Cryptography.Aes]::Create()
$aes.Key  = $key
$aes.IV   = $iv
$aes.Mode = [System.Security.Cryptography.CipherMode]::CBC

$plainBytes = [System.IO.File]::ReadAllBytes($Path)
$encryptor  = $aes.CreateEncryptor()
$cipherBytes = $encryptor.TransformFinalBlock($plainBytes, 0, $plainBytes.Length)

$outPath = "$Path.enc"
$outStream = [System.IO.File]::Create($outPath)
$outStream.Write($salt, 0, $salt.Length)
$outStream.Write($iv, 0, $iv.Length)
$outStream.Write($cipherBytes, 0, $cipherBytes.Length)
$outStream.Close()

Remove-Item $Path -Force

Write-Host "[OK] Backup criptografado: $outPath"
