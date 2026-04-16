@echo off
title Gerador de Relatorio - Hospital Cafe Filho
color 0B
echo ===================================================
echo     GERADOR DE PLANILHA EXCEL (MENSAL/BPA)
echo ===================================================
echo.
REM Chama o script Python que constroi o Excel
python relatorio_mensal.py
echo.
echo ===================================================
echo Relatorio finalizado! Abrindo a pasta para voce...
echo ===================================================
REM O comando 'explorer .' abre automaticamente a pasta atual no Windows!
explorer .
echo.
pause