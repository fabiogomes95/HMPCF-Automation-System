@echo off
title HMPCF - BPA (janela de diagnostico)
cd /d "%~dp0"
REM O BPA liga sozinho com o Windows (tarefa HMPCF-BPA, sem janela). Este .bat
REM e so pra diagnostico: roda com a janela aberta pra ver erros na tela.
REM Feche o BPA que estiver rodando antes (ou rode o instalar.ps1 depois).
echo.
echo  BPA local em http://localhost:8503  (Ctrl+C para encerrar)
echo.
"%~dp0.venv\Scripts\python.exe" executar.py
pause
