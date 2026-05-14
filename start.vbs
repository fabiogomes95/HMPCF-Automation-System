Set WshShell = CreateObject("WScript.Shell")
' Executa o arquivo .bat de forma totalmente invisível (o número 0 faz isso)
WshShell.Run chr(34) & "iniciar.bat" & chr(34), 0
Set WshShell = Nothing