@echo off
chcp 65001 >nul

:: Verifica se está rodando como Administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Este script precisa ser executado como Administrador.
    echo     Clique com o botao direito no arquivo e escolha:
    echo     "Executar como administrador"
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   HMPCF -- Configurar WinRM (servidor)
echo ==========================================
echo.
echo Este script habilita o acesso remoto via PowerShell
echo para que a equipe possa rodar scripts sem precisar
echo usar este PC fisicamente.
echo.
pause

echo.
echo [1/5] Habilitando WinRM...
powershell -NoProfile -Command "Enable-PSRemoting -Force -SkipNetworkProfileCheck" >nul 2>&1
if %errorlevel% neq 0 (
    powershell -NoProfile -Command "winrm quickconfig -q"
)

echo [2/5] Configurando autenticacao basica...
powershell -NoProfile -Command "Set-Item WSMan:\localhost\Service\Auth\Basic -Value $true -Force" >nul
powershell -NoProfile -Command "Set-Item WSMan:\localhost\Service\AllowUnencrypted -Value $true -Force" >nul

echo [3/5] Adicionando maquinas confiaveis (rede local)...
powershell -NoProfile -Command "Set-Item WSMan:\localhost\Client\TrustedHosts -Value '*' -Force" >nul

echo [4/5] Abrindo porta 5985 no firewall...
netsh advfirewall firewall delete rule name="WinRM-HTTP-HMPCF" >nul 2>&1
netsh advfirewall firewall add rule name="WinRM-HTTP-HMPCF" dir=in localport=5985 protocol=TCP action=allow profile=private,domain >nul

echo [5/5] Configurando servico para iniciar automaticamente...
sc config WinRM start= auto >nul
net start WinRM >nul 2>&1

echo.
echo ==========================================
echo  Configuracao concluida!
echo.
echo  IP deste PC:
ipconfig | findstr /i "IPv4"
echo.
echo  Anote o IP acima -- voce vai precisar dele
echo  para configurar o outro computador.
echo ==========================================
echo.
pause
