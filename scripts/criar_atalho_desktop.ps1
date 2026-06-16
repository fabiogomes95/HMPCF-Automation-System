# Cria atalho do HMPCF na area de trabalho de TODOS os usuarios desta maquina

$batPath  = "C:\HMPCF-Automation-System\ABRIR_HMPCF.bat"
$iconPath = "C:\HMPCF-Automation-System\scripts\hmpcf.ico"

# Desktops para criar o atalho
$desktops = @(
    [System.Environment]::GetFolderPath("CommonDesktopDirectory"),  # Todos os usuarios
    [System.Environment]::GetFolderPath("Desktop")                  # Usuario atual
)

$shell = New-Object -ComObject WScript.Shell

foreach ($desktop in $desktops) {
    if (-not (Test-Path $desktop)) { continue }

    $lnkPath = Join-Path $desktop "HMPCF - Sistema Hospitalar.lnk"
    $sc = $shell.CreateShortcut($lnkPath)
    $sc.TargetPath       = "cmd.exe"
    $sc.Arguments        = "/c `"$batPath`""
    $sc.WorkingDirectory = "C:\HMPCF-Automation-System"
    $sc.Description      = "Abrir Sistema HMPCF"
    $sc.WindowStyle      = 7   # Minimizado (esconde janela preta do cmd)

    # Usa icone personalizado se existir, senao usa icone medico do sistema
    if (Test-Path $iconPath) {
        $sc.IconLocation = "$iconPath,0"
    } else {
        $sc.IconLocation = "C:\Windows\System32\imageres.dll,56"  # icone de monitor/app
    }

    $sc.Save()
    Write-Host "[OK] Atalho criado em: $lnkPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "Atalho 'HMPCF - Sistema Hospitalar' disponivel na area de trabalho." -ForegroundColor Cyan
Write-Host "Clique duas vezes para abrir o sistema." -ForegroundColor Cyan
