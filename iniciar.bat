@echo off
:: 1. Entra na pasta onde o arquivo .bat está (Pasta do Projeto)
cd /d "%~dp0"

:: 2. VERIFICAÇÃO: A porta 8001 já está ativa? 
:: (Tudo na mesma linha para não dar erro)
netstat -ano | findstr :8001 >nul

:: Se o erro for 0 (porta encontrada), o servidor já está ligado
if %errorlevel% equ 0 (
    echo [OK] Servidor HMPCF ja esta rodando. Abrindo interface...
    start msedge http://localhost:8001
    exit
)

:: 3. SE NÃO ESTIVER RODANDO: Procura o caminho do Python neste PC
echo [!] Servidor desligado. Localizando Python...
for /f "delims=" %%i in ('python -c "import sys; print(sys.executable)"') do set "PY_PATH=%%i"
set "PYW_PATH=%PY_PATH:python.exe=pythonw.exe%"

:: 4. INICIA O SERVIDOR: Usa o pythonw para não abrir janela preta
echo [!] Iniciando novo servidor HMPCF...
start "" "%PYW_PATH%" app_painel.py

:: 5. ESPERA O MOTOR ACORDAR E ABRE O NAVEGADOR
:: Aguarda 2 segundos para dar tempo do banco de dados carregar na RAM
timeout /t 2 /nobreak >nul
start msedge http://localhost:8001

exit