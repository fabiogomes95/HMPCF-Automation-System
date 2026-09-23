@echo off
REM Roda a conferencia (digitado x lote de producao no Firebird) dos ultimos 7
REM dias e salva relatorio em conferencia_relatorios\ (CPF mascarado no arquivo).
REM Chamado pela Tarefa Agendada "HMPCF-Conferencia-Semanal" (toda sexta-feira).
cd /d "%~dp0"
if not exist "conferencia_relatorios" mkdir "conferencia_relatorios"
REM Python do BPA: bpa\.venv (instalar.ps1); enquanto nao instalado, o antigo dashboard\.venv.
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=%~dp0..\dashboard\.venv\Scripts\python.exe"
"%PY%" conferencia.py --relatorio >> "conferencia_relatorios\conferencia_semanal.log" 2>&1
