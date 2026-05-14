@echo off
cd /d "%~dp0"

:: 1. MATAR PROCESSOS: Encerra qualquer Python que ficou travado escondido
taskkill /f /im python.exe /t >nul 2>&1
taskkill /f /im pythonw.exe /t >nul 2>&1

:: 2. LIMPAR PORTA: Mata especificamente quem estiver usando a porta 8001 (Eel)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001') do taskkill /f /pid %%a >nul 2>&1

:: 3. ESPERA 1 SEGUNDO: Para o Windows liberar a porta de verdade
timeout /t 1 /nobreak >nul

:: 4. ACHAR O PYTHON: Pergunta ao sistema onde ele está
for /f "delims=" %%i in ('python -c "import sys; print(sys.executable)"') do set "PY_PATH=%%i"
set "PYW_PATH=%PY_PATH:python.exe=pythonw.exe%"

:: 5. ABRIR: Inicia o painel sem janela preta
start "" "%PYW_PATH%" app_painel.py
exit