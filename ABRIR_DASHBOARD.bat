@echo off
chcp 65001 >nul
cd /d "%~dp0dashboard"
echo Iniciando Painel Gerencial HMPCF, aguarde...
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8502
