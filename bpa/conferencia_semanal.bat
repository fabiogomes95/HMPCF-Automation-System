@echo off
REM Roda a conferencia (digitado x lote de producao no Firebird) dos ultimos 7
REM dias e salva relatorio em conferencia_relatorios\ (CPF mascarado no arquivo).
REM Chamado pela Tarefa Agendada "HMPCF-Conferencia-Semanal" (toda sexta-feira).
cd /d "%~dp0"
if not exist "conferencia_relatorios" mkdir "conferencia_relatorios"
"..\dashboard\.venv\Scripts\python.exe" conferencia.py --relatorio >> "conferencia_relatorios\conferencia_semanal.log" 2>&1
