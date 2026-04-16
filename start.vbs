' =========================================================================
' LANÇADOR INVISÍVEL DO SISTEMA B.P.A. (VERSÃO PYTHON GLOBAL)
' =========================================================================
Set WshShell = CreateObject("WScript.Shell")

' 1. Liga o servidor silenciosamente usando o Python direto do sistema
WshShell.Run "cmd /c python app.py", 0, False

' 2. O robô espera 2 segundos para o servidor aquecer
WScript.Sleep 2000

' 3. Abre a tela do sistema automaticamente no navegador
WshShell.Run "http://127.0.0.1:5000"