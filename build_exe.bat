@echo off
title HMPCF - Build Instalador
color 0B
echo ===================================================
echo     HMPCF - Build do Instalador (.exe)
echo ===================================================
echo.

:: 1. Entra na pasta do projeto
cd /d "%~dp0"

:: 2. Verifica se PyInstaller está instalado
echo [!] Verificando PyInstaller...
python -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] PyInstaller nao instalado. Instalando...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao instalar PyInstaller.
        pause
        exit /b 1
    )
)

:: 3. Verifica se requests está instalado (para auto-update)
python -c "import requests" 2>nul
if %errorlevel% neq 0 (
    echo [!] Instalando requests...
    pip install requests
)

:: 4. Remove build anterior
echo [!] Limpando builds anteriores...
if exist "dist\HMPCF" rmdir /s /q "dist\HMPCF"
if exist "build" rmdir /s /q "build"
if exist "HMPCF.spec" del /f /q "HMPCF.spec"

:: 5. Build do executável
echo.
echo [!] Gerando executavel... (pode levar alguns minutos)
echo.
python -m PyInstaller ^
    --name "HMPCF" ^
    --onefile ^
    --console ^
    --icon "assets\robo-icon.ico" ^
    --add-data "web_recepcao/index.html;web_recepcao" ^
    --add-data "web_recepcao/style.css;web_recepcao" ^
    --add-data "web_recepcao/script.js;web_recepcao" ^
    --add-data "web_recepcao/logo.png;web_recepcao" ^
    --add-data "web_recepcao/assets/bootstrap.min.css;web_recepcao/assets" ^
    --add-data "web_recepcao/assets/bootstrap.bundle.min.js;web_recepcao/assets" ^
    --add-data "web_painel/index.html;web_painel" ^
    --add-data "web_painel/analise.html;web_painel" ^
    --add-data "web_painel/integracao.html;web_painel" ^
    --add-data "web_painel/automacao.html;web_painel" ^
    --add-data "web_painel/digitacao.html;web_painel" ^
    --add-data "web_painel/triagem.html;web_painel" ^
    --add-data "web_painel/robo.html;web_painel" ^
    --add-data "web_painel/style.css;web_painel" ^
    --add-data "version.json;." ^
    --hidden-import "eel" ^
    --hidden-import "firebirdsql" ^
    --hidden-import "pandas" ^
    --hidden-import "seaborn" ^
    --hidden-import "openpyxl" ^
    --hidden-import "matplotlib" ^
    --hidden-import "weasyprint" ^
    --hidden-import "pyautogui" ^
    --hidden-import "keyboard" ^
    --hidden-import "gspread" ^
    --hidden-import "google.auth" ^
    main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao gerar executavel.
    pause
    exit /b 1
)

:: 6. Sucesso!
echo.
echo ===================================================
echo     ✅ INSTALADOR GERADO COM SUCESSO!
echo ===================================================
echo.
echo Arquivo: dist\HMPCF.exe
echo.
echo Para distribuir:
echo   1. Copie HMPCF.exe para o computador destino
echo   2. Execute HMPCF.exe
echo   3. O sistema vai verificar atualizacoes no GitHub
echo   4. Depois abre a Recepcao e o Painel automaticamente
echo.
echo Tamanho:
dir "dist\HMPCF.exe" 2>nul
echo.
pause
